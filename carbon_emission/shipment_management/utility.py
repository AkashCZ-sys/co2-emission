import uuid
from decimal import Decimal
from haversine import haversine
import searoute as sr
import requests
from django.db.models import Q
from enum import Enum


class BaseEnum(Enum):
    def __init__(self, code, description):
        self.CODE = code
        self.DESCRIPTION = description

    @classmethod
    def get_module_id_by_name(cls, module_name):
        if not module_name:
            return None
        cleaned_input = module_name.strip().lower()
        for module in cls:
            if module.DESCRIPTION.strip().lower() == cleaned_input:
                return module.CODE
        return None

    @classmethod
    def get_module_name_by_id(cls, module_id):
        if not module_id:
            return None
        for module in cls:
            if module.CODE == module_id:
                return module.DESCRIPTION
        return None

    @classmethod
    def choices(cls):
        return [(module.CODE, module.DESCRIPTION) for module in cls]


class FuelTypeEnum(BaseEnum):
    DIESEL = (1, "Diesel")
    LNG = (2, "Liquefied Natural Gas (LNG)")
    HFO = (3, "Heavy Fuel Oil (HFO)")
    VLSFO = (4, "Very Low Sulfur Fuel Oil (VLSFO)")
    JET_FUEL = (5, "Jet Fuel")
    ELECTRIC = (6, "Electric")


class TransportModeEnum(BaseEnum):
    OCEAN = (5, "Ocean")
    AIR = (10, "Air")
    ROAD = (15, "Road")
    RAIL = (20, "Rail")


class ServiceTypeEnum(BaseEnum):
    CY = (5, "CY")
    CFS = (10, "CFS")


class CargoTypeEnum(BaseEnum):
    NORMAL = (5, "Normal")
    REEFER = (10, "Reefer")
    DG = (15, "Dangerous Goods")


EMISSION_FACTORS = {
    FuelTypeEnum.DIESEL.CODE: 2.68,
    FuelTypeEnum.LNG.CODE: 2.75,
    FuelTypeEnum.HFO.CODE: 3.114,
    FuelTypeEnum.VLSFO.CODE: 3.151,
    FuelTypeEnum.JET_FUEL.CODE: 2.54,
    FuelTypeEnum.ELECTRIC.CODE: 0.0,
}

ROAD_FACTORS = {
    "HEAVY": 62.0,
    "MEDIUM": 83.0,
    "LIGHT": 151.0,
}

RAIL_FACTORS = {
    "ELECTRIC": 6.0,
    "DIESEL": 22.0,
    "DEFAULT": 30.0,
}

AIR_FACTORS = {
    "FREIGHTER": 750.0,
    "PASSENGER_BELLY": 602.0,
}

OCEAN_FACTORS = {
    "CONTAINER_VESSEL": 16.0,
    "BULK_CARRIER": 7.0,
    "RORO": 30.0,
    "FEEDER_VESSEL": 22.0,
}

CONTAINER_ADJUSTMENTS = {
    "20_FOOT": 1.0,
    "40_FOOT": 0.85,
    "REEFER": 1.35,
    "ISO_TANK": 1.20,
}

HANDLING_FACTOR = 0.003

MAX_DECIMAL_VALUE = Decimal("9999999999.99")


def clamp_decimal(value: Decimal) -> Decimal:
    if value > MAX_DECIMAL_VALUE:
        return MAX_DECIMAL_VALUE
    if value < -MAX_DECIMAL_VALUE:
        return -MAX_DECIMAL_VALUE
    return value


def get_emission_factor(fuel_type_code):
    return EMISSION_FACTORS.get(fuel_type_code, 0.0)


def enum_search_q(enum_cls, field_name, search_value):
    code = enum_cls.get_module_id_by_name(search_value)
    if code is not None:
        return Q(**{field_name: code})
    return Q()


def apply_fk_filter(queryset, field, value):
    if not value:
        return queryset
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return queryset.filter(**{f"{field}_id": int(value)})
    return queryset.filter(**{f"{field}__name__icontains": value})


def generate_booking_id():
    return f"VBK-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def calculate_sea_distance(origin_lat, origin_lon, destination_lat, destination_lon):
    route = sr.searoute(
        [float(origin_lon), float(origin_lat)],
        [float(destination_lon), float(destination_lat)],
    )
    return route.properties["length"]


def calculate_road_distance(origin_lat, origin_lon, destination_lat, destination_lon):
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{origin_lon},{origin_lat};"
        f"{destination_lon},{destination_lat}"
        f"?overview=false"
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not data.get("routes"):
        raise ValueError("No road route found.")
    return data["routes"][0]["distance"] / 1000.0


def calculate_distance(segment) -> float:
    origin_lat = float(segment.origin_latitude)
    origin_lon = float(segment.origin_longitude)
    dest_lat = float(segment.destination_latitude)
    dest_lon = float(segment.destination_longitude)

    origin = (origin_lat, origin_lon)
    destination = (dest_lat, dest_lon)
    mode = segment.transportation_mode

    if mode == TransportModeEnum.OCEAN.CODE:
        route = sr.searoute([origin_lon, origin_lat], [dest_lon, dest_lat])
        return route["properties"]["length"]
    elif mode == TransportModeEnum.AIR.CODE:
        return haversine(origin, destination)
    elif mode == TransportModeEnum.ROAD.CODE:
        return calculate_road_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    elif mode == TransportModeEnum.RAIL.CODE:
        return haversine(origin, destination) * 1.15
    return 0.0


# ---------------------------------------------------------------------------
# Per-segment Emission Calculation Service
# ---------------------------------------------------------------------------

class EmissionCalculationService:
    """
    Calculates emission for a single segment given pre-computed shipment-level
    values (cargo_weight, container_adjustment, load_factor).
    """

    def __init__(self, segment, cargo_weight, container_adjustment, load_factor):
        self.segment = segment
        self.cargo_weight = float(cargo_weight)
        self.container_adjustment = float(container_adjustment)
        self.load_factor = float(load_factor)

    def get_emission_factor(self) -> float:
        mode = self.segment.transportation_mode
        if mode == TransportModeEnum.OCEAN.CODE:
            return OCEAN_FACTORS.get(
                getattr(self.segment, "freight_type", None) or "CONTAINER_VESSEL",
                16.0,
            )
        elif mode == TransportModeEnum.AIR.CODE:
            return AIR_FACTORS.get(
                getattr(self.segment, "freight_type", None) or "FREIGHTER",
                750.0,
            )
        elif mode == TransportModeEnum.ROAD.CODE:
            return ROAD_FACTORS.get(
                getattr(self.segment, "freight_type", None) or "HEAVY",
                62.0,
            )
        elif mode == TransportModeEnum.RAIL.CODE:
            return RAIL_FACTORS.get(
                getattr(self.segment, "freight_type", None) or "DEFAULT",
                30.0,
            )
        return 0.0

    def calculate(self) -> dict:
        distance = float(self.segment.distance_km or 0) or calculate_distance(self.segment)
        emission_factor = self.get_emission_factor()

        # Core formula: (distance_km * weight_t * g/tkm * adjustments) / 1000  → kg CO₂
        transport_emission = (
                                     distance
                                     * self.cargo_weight
                                     * emission_factor
                                     * self.container_adjustment
                                     * self.load_factor
                             ) / 1000.0

        handling = 0.0
        so = getattr(self.segment, "shipment_order", None)
        if (
                so is not None
                and getattr(so, "consider_handling_emission", False)
                and self.segment.transportation_mode == TransportModeEnum.OCEAN.CODE
        ):
            handling = self.cargo_weight * distance * HANDLING_FACTOR

        transport_emission = min(transport_emission, float(MAX_DECIMAL_VALUE))
        handling = min(handling, float(MAX_DECIMAL_VALUE))
        total = min(transport_emission + handling, float(MAX_DECIMAL_VALUE))

        return {
            # keys used when persisting to ShipmentSegmentEmission
            "distance_km": round(distance, 3),
            "cargo_weight_tonne": self.cargo_weight,
            "emission_factor": emission_factor,
            "container_adjustment_factor": self.container_adjustment,
            "load_factor": self.load_factor,
            "handling_emission_kg": round(handling, 3),
            "co2_kg": round(total, 3),
            # extra metadata stored in JSON field
            "calculation_metadata": {
                "transport_mode": self.segment.transportation_mode,
                "transport_emission_kg": round(transport_emission, 3),
            },
        }


# ---------------------------------------------------------------------------
# Shipment-level Emission Calculator
# ---------------------------------------------------------------------------

class ShipmentEmissionCalculator:

    def __init__(self, shipment_order):
        self.shipment_order = shipment_order

    def get_total_cargo_weight(self) -> Decimal:
        total = Decimal("0")
        for load in self.shipment_order.load_details.all():
            total += Decimal(str(load.weight_in_tonne)) * Decimal(str(load.quantity))
        return total

    def get_container_adjustment(self) -> Decimal:
        total_qty = Decimal("0")
        weighted_sum = Decimal("0")
        for load in self.shipment_order.load_details.all():
            factor = Decimal(str(CONTAINER_ADJUSTMENTS.get(load.container_type, 1.0)))
            qty = Decimal(str(load.quantity))
            weighted_sum += factor * qty
            total_qty += qty
        if total_qty == 0:
            return Decimal("1.0")
        return weighted_sum / total_qty

    def get_load_factor(self, cargo_weight: Decimal) -> Decimal:
        if self.shipment_order.container_load_type == "FCL":
            return Decimal("1.0")
        capacity = Decimal("40.0")
        factor = cargo_weight / capacity
        return max(Decimal("0.1"), min(factor, Decimal("1.0")))

    def calculate(self) -> dict:
        """
        Calculate emissions for every segment, persist ShipmentSegmentEmission
        rows, update calculated_distance_km on each segment, and return a
        summary dict.
        """
        from shipment_management.models import ShipmentSegmentEmission  # avoid circular import

        cargo_weight = self.get_total_cargo_weight()
        container_adj = self.get_container_adjustment()
        load_factor = self.get_load_factor(cargo_weight)

        total_co2 = Decimal("0")
        segment_results = []

        for segment in self.shipment_order.segments.all().order_by("sequence_number"):
            result = EmissionCalculationService(
                segment=segment,
                cargo_weight=cargo_weight,
                container_adjustment=container_adj,
                load_factor=load_factor,
            ).calculate()

            co2_decimal = clamp_decimal(Decimal(str(result["co2_kg"])))
            result["co2_kg"] = float(co2_decimal)

            # ----------------------------------------------------------------
            # FIX: persist (or update) the emission row for this segment
            # ----------------------------------------------------------------
            ShipmentSegmentEmission.objects.update_or_create(
                shipment_segment=segment,
                defaults={
                    "cargo_weight_tonne": Decimal(str(result["cargo_weight_tonne"])),
                    "distance_km": Decimal(str(result["distance_km"])),
                    "emission_factor": Decimal(str(result["emission_factor"])),
                    "load_factor": Decimal(str(result["load_factor"])),
                    "container_adjustment_factor": Decimal(str(result["container_adjustment_factor"])),
                    "handling_emission_kg": Decimal(str(result["handling_emission_kg"])),
                    "co2_kg": co2_decimal,
                    "calculation_metadata": result.get("calculation_metadata", {}),
                },
            )

            # Also store the calculated distance back on the segment
            segment.calculated_distance_km = Decimal(str(result["distance_km"]))
            segment.save(update_fields=["calculated_distance_km"])

            segment_results.append(result)
            total_co2 += co2_decimal

        grand_total = clamp_decimal(total_co2)

        return {
            "cargo_weight": float(cargo_weight),
            "container_adjustment": float(container_adj),
            "load_factor": float(load_factor),
            "segments": segment_results,
            "grand_total": round(float(grand_total), 3),
        }
