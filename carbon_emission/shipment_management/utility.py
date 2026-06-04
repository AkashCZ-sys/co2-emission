import datetime
import re
import uuid
from decimal import Decimal
from enum import Enum
from haversine import haversine
import searoute as sr

from django.db.models import Q


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


class IncotermEnum(BaseEnum):
    EXW = (5, "ExWorks")
    FOB = (10, "FreeOnBoard")
    FCA = (15, "FreeCarrier")
    DAP = (20, "DeliveredAtPlace")
    FAS = (25, "Free Alongside Ship")
    CFR = (30, "Cost and Freight")
    CIS = (35, "Cost, Insurance and Freight")
    CPT = (40, "Carriage Paid To")
    CIP = (45, "Carriage and Insurance Paid To")
    DAF = (50, "Delivered At Frontier")
    DPU = (55, "Delivered at Place Unloaded")
    DDP = (60, "Delivered Duty Paid")
    DDU = (65, "Delivered Duty Unpaid")


EMISSION_FACTORS = {
    FuelTypeEnum.DIESEL.CODE: 2.68,
    FuelTypeEnum.LNG.CODE: 2.75,
    FuelTypeEnum.HFO.CODE: 3.114,
    FuelTypeEnum.VLSFO.CODE: 3.151,
    FuelTypeEnum.JET_FUEL.CODE: 2.54,
    FuelTypeEnum.ELECTRIC.CODE: 0.0,
}

ROAD_FACTORS = {
    "HEAVY_TRUCK": 62.0,
    "MEDIUM_TRUCK": 83.0,
    "LIGHT_TRUCK": 151.0,
}

RAIL_FACTORS = {
    "ELECTRIC": 6.0,
    "DIESEL": 22.0,
}

AIR_FACTORS = {
    "FREIGHTER": 602.0,
    "BELLY": 520.0,
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
    """Clamp a Decimal to the safe DB range so we never overflow."""
    if value > MAX_DECIMAL_VALUE:
        return MAX_DECIMAL_VALUE
    if value < -MAX_DECIMAL_VALUE:
        return -MAX_DECIMAL_VALUE
    return value


def get_emission_factor(fuel_type):
    return EMISSION_FACTORS.get(fuel_type, 0.0)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

DATE_FOLDER_FORMAT = "%Y/%m/%d"

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%y/%m/%d",
    "%y-%m-%d",
    "%y\\%m\\%d",
    "%Y/%m",
    "%m-%d-%Y",
    "%m/%d/%Y",
]


def parse_search_date(value: str):
    """Try to parse a date string from multiple formats. Returns date or None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            # FIX: was bare datetime.strptime — must be datetime.datetime.strptime
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_year_month(value: str):
    """
    Parses YYYY/MM, YYYY-MM, MM/YYYY, MM-YYYY, MM/YY, MM-YY.
    Returns (year, month) or None.
    """
    value = value.strip()

    match_ym = re.match(r"^(\d{4})[\/\-](\d{1,2})$", value)
    if match_ym:
        year, month = int(match_ym.group(1)), int(match_ym.group(2))
        if 1 <= month <= 12:
            return year, month
        return None

    match_my4 = re.match(r"^(\d{1,2})[\/\-](\d{4})$", value)
    if match_my4:
        month, year = int(match_my4.group(1)), int(match_my4.group(2))
        if 1 <= month <= 12:
            return year, month
        return None

    match_my2 = re.match(r"^(\d{1,2})[\/\-](\d{2})$", value)
    if match_my2:
        month, year = int(match_my2.group(1)), int(match_my2.group(2))
        if 1 <= month <= 12:
            return 2000 + year, month
        return None

    return None


def parse_day_month(value: str):
    """Parses DD/MM or DD-MM. Returns (month, day) or None."""
    value = value.strip()
    match = re.match(r"^(\d{1,2})[\/\-](\d{1,2})$", value)
    if not match:
        return None
    day, month = int(match.group(1)), int(match.group(2))
    if 1 <= day <= 31 and 1 <= month <= 12:
        return month, day
    return None


def get_custom_folder_path(document_type_id, is_temporary, data_dict: dict,
                           application_name, le_id=None, document_type_name=""):
    # FIX: was datetime.now() — must be datetime.datetime.now()
    current_date = datetime.datetime.now().strftime(DATE_FOLDER_FORMAT)
    return current_date


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------

def enum_search_q(enum_cls, field_name, search_value):
    """Builds a Q() object for enum name/description search."""
    code = enum_cls.get_module_id_by_name(search_value)
    if code is not None:
        return Q(**{field_name: code})
    return Q()


def build_global_search_q(search_value):
    q = Q()
    if not search_value:
        return q

    search_value = search_value.strip()
    search_lower = search_value.lower()

    # Text search
    q |= Q(vendor_booking_number__icontains=search_value)
    q |= Q(shipper__icontains=search_value)
    q |= Q(consignee__icontains=search_value)
    q |= Q(place_of_receipt__icontains=search_value)
    q |= Q(place_of_delivery__icontains=search_value)
    q |= Q(vessel_name__icontains=search_value)
    q |= Q(customer__name__icontains=search_value)
    q |= Q(vendor__name__icontains=search_value)
    q |= Q(origin_agent__name__icontains=search_value)
    q |= Q(destination_agent__name__icontains=search_value)
    q |= Q(pol__name__icontains=search_value)
    q |= Q(pod__name__icontains=search_value)

    # Enum search
    enum_maps = {
        "transportation_mode": TransportModeEnum,
        "service_type": ServiceTypeEnum,
        "cargo_type": CargoTypeEnum,
        "incoterm": IncotermEnum,
    }
    for field, enum_cls in enum_maps.items():
        for enum_member in enum_cls:
            if search_lower in enum_member.DESCRIPTION.lower():
                q |= Q(**{field: enum_member.CODE})

    # Float search (exact)
    try:
        if re.match(r"^\d+\.$", search_value) or re.match(r"^\d+\.\d+$", search_value):
            base = float(search_value)
            decimal_part = search_value.split(".")[1] if "." in search_value else ""
            precision = len(decimal_part)
            tolerance = 10 ** (-precision) if precision > 0 else 1
            min_value = base
            max_value = base + tolerance
            q |= (
                    Q(volume_booked__gte=min_value, volume_booked__lt=max_value) |
                    Q(volume_actual__gte=min_value, volume_actual__lt=max_value) |
                    Q(weight_booked__gte=min_value, weight_booked__lt=max_value) |
                    Q(weight_actual__gte=min_value, weight_actual__lt=max_value) |
                    Q(quantity_booked__gte=min_value, quantity_booked__lt=max_value) |
                    Q(quantity_actual__gte=min_value, quantity_actual__lt=max_value)
            )
    except ValueError:
        pass

    # Integer search
    if search_value.isdigit():
        int_value = int(search_value)

        q |= Q(vendor_booking_status=int_value)
        q |= Q(transportation_mode=int_value)
        q |= Q(service_type=int_value)
        q |= Q(cargo_type=int_value)
        q |= Q(incoterm=int_value)
        q |= Q(payment_terms=int_value)
        q |= Q(equipment_count=int_value)

        q |= Q(volume_booked=int_value)
        q |= Q(volume_actual=int_value)
        q |= Q(weight_booked=int_value)
        q |= Q(weight_actual=int_value)
        q |= Q(quantity_booked=int_value)
        q |= Q(quantity_actual=int_value)

        if len(search_value) == 4:
            q |= Q(created_on__year=int_value)
            q |= Q(cargo_readiness_date__year=int_value)

        if len(search_value) == 2:
            if 1 <= int_value <= 12:
                q |= Q(created_on__month=int_value)
                q |= Q(cargo_readiness_date__month=int_value)
            if 1 <= int_value <= 31:
                q |= Q(created_on__day=int_value)
                q |= Q(cargo_readiness_date__day=int_value)

    # Year-month
    ym = parse_year_month(search_value)
    if ym:
        year, month = ym
        q |= Q(created_on__year=year, created_on__month=month)
        q |= Q(cargo_readiness_date__year=year, cargo_readiness_date__month=month)

    # Day-month
    dm = parse_day_month(search_value)
    if dm:
        month, day = dm
        q |= Q(created_on__month=month, created_on__day=day)
        q |= Q(cargo_readiness_date__month=month, cargo_readiness_date__day=day)

    # Full date
    parsed_date = parse_search_date(search_value)
    if parsed_date:
        q |= Q(created_on__date=parsed_date)
        q |= Q(cargo_readiness_date__date=parsed_date)

    # Boolean
    if search_lower in ("active", "true"):
        q |= Q(is_active=True)
    elif search_lower in ("inactive", "false"):
        q |= Q(is_active=False)

    return q


def apply_fk_filter(queryset, field, value):
    """Filter queryset by FK id or related name."""
    if not value:
        return queryset
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return queryset.filter(**{f"{field}_id": int(value)})
    return queryset.filter(**{f"{field}__name__icontains": value})


def generate_booking_id():
    """Generates a unique booking ID."""
    return f"VBK-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Standalone helpers (kept for backward compatibility)
# ---------------------------------------------------------------------------

def calculate_handling_emission(shipment):
    """
    Standalone version (not a method). Pass the shipment object directly.
    FIX: original version used `self` but was defined as a bare function.
    """
    if not shipment.consider_handling_emission:
        return 0

    total_containers = sum(
        x.quantity for x in shipment.load_details.all()
    )

    handling = 0
    previous_mode = None

    for segment in shipment.segments.all().order_by("sequence_no"):
        current_mode = segment.transport_mode

        if previous_mode:
            if current_mode == "OCEAN":
                handling += total_containers * 5
            elif current_mode == "RAIL":
                handling += total_containers * 3
            elif current_mode == "ROAD":
                handling += total_containers * 1
            elif current_mode == "INLAND_WATERWAY":
                handling += total_containers * 5

        previous_mode = current_mode

    return handling


def get_load_factor(shipment, cargo_weight):
    """Standalone version. FIX: original used `self`."""
    if shipment.container_load_type == "FCL":
        return 1.0
    capacity = 40.0
    factor = cargo_weight / capacity
    return max(0.1, min(factor, 1.0))


def get_container_adjustment(shipment):
    """Standalone version. FIX: original used `self` and mixed Decimal/float."""
    total_qty = 0
    weighted_sum = 0.0

    for load in shipment.load_details.all():
        factor = float(CONTAINER_ADJUSTMENTS.get(load.container_type, 1.0))
        weighted_sum += factor * float(load.quantity)
        total_qty += float(load.quantity)

    if total_qty == 0:
        return 1.0

    return weighted_sum / total_qty


def get_total_cargo_weight(shipment):
    """Standalone version. FIX: original used `self`."""
    total_weight = 0.0
    for load in shipment.load_details.all():
        total_weight += float(load.weight_tonne) * float(load.quantity)
    return total_weight


# ---------------------------------------------------------------------------
# EmissionCalculationService  (per-segment, used internally)
# ---------------------------------------------------------------------------

class EmissionCalculationService:
    """
    Calculates emission for a single segment given pre-computed shipment-level
    values (cargo_weight, container_adjustment, load_factor).

    FIX: Original class took only `shipment` and recalculated everything
    inside calculate_segment_emission, but ShipmentEmissionCalculator was
    calling it with (segment=…, cargo_weight=…, …) — signature mismatch.
    Now accepts the correct arguments.
    """

    def __init__(self, segment, cargo_weight, container_adjustment, load_factor):
        self.segment = segment
        self.cargo_weight = float(cargo_weight)
        self.container_adjustment = float(container_adjustment)
        self.load_factor = float(load_factor)

    def get_emission_factor(self):
        mode = self.segment.transportation_mode
        if mode == 5:  # Ocean
            return OCEAN_FACTORS.get(self.segment.freight_type, 16.0)
        elif mode == 10:  # Air
            return AIR_FACTORS.get(self.segment.freight_type, 602.0)
        elif mode == 15:  # Road
            return ROAD_FACTORS.get(self.segment.freight_type, 62.0)
        elif mode == 20:  # Rail
            return RAIL_FACTORS.get(self.segment.freight_type, 22.0)
        return 0.0

    def calculate(self):
        distance = float(calculate_distance(self.segment))
        emission_factor = self.get_emission_factor()

        # Core formula: (distance_km * weight_t * g_per_tkm * adjustments) / 1000
        # Result is in kg CO2e
        transport_emission = (
                                     distance
                                     * self.cargo_weight
                                     * emission_factor
                                     * self.container_adjustment
                                     * self.load_factor
                             ) / 1000.0

        handling = 0.0
        if (
                getattr(self.segment, "shipment", None)
                and self.segment.shipment.consider_handling_emission
                and self.segment.transportation_mode == 5
        ):
            handling = self.cargo_weight * distance * HANDLING_FACTOR

        # FIX: clamp to DB-safe range before returning
        transport_emission = min(transport_emission, float(MAX_DECIMAL_VALUE))
        handling = min(handling, float(MAX_DECIMAL_VALUE))
        total = min(transport_emission + handling, float(MAX_DECIMAL_VALUE))

        return {
            "transport_mode": self.segment.transportation_mode,
            "route_type": "CALCULATED",
            "distance_km": round(distance, 3),
            "cargo_weight_t": self.cargo_weight,
            "emission_factor_g_per_tkm": emission_factor,
            "container_adjustment": self.container_adjustment,
            "load_factor": self.load_factor,
            "transport_emission": round(transport_emission, 3),
            "handling_emission": round(handling, 3),
            # Keep co2e_kg key so ShipmentEmissionCalculator.calculate() works
            "co2e_kg": round(total, 3),
        }


# ---------------------------------------------------------------------------
# ShipmentEmissionCalculator  (top-level orchestrator)
# ---------------------------------------------------------------------------

class ShipmentEmissionCalculator:

    def __init__(self, shipment):
        self.shipment = shipment

    def get_total_cargo_weight(self) -> Decimal:
        # FIX: was mixing Decimal("0") init with float arithmetic
        total = Decimal("0")
        for load in self.shipment.load_details.all():
            total += Decimal(str(load.weight_tonne)) * Decimal(str(load.quantity))
        return total

    def get_container_adjustment(self) -> Decimal:
        # FIX: was mixing Decimal and float without conversion
        total_qty = Decimal("0")
        weighted_sum = Decimal("0")

        for load in self.shipment.load_details.all():
            factor = Decimal(str(
                CONTAINER_ADJUSTMENTS.get(load.container_type, 1.0)
            ))
            qty = Decimal(str(load.quantity))
            weighted_sum += factor * qty
            total_qty += qty

        if total_qty == 0:
            return Decimal("1.0")

        return weighted_sum / total_qty

    def get_load_factor(self, cargo_weight: Decimal) -> Decimal:
        if self.shipment.container_load_type == "FCL":
            return Decimal("1.0")

        capacity = Decimal("40.0")
        factor = cargo_weight / capacity
        return max(Decimal("0.1"), min(factor, Decimal("1.0")))

    def calculate_handling_emission(self) -> Decimal:
        if not self.shipment.consider_handling_emission:
            return Decimal("0")

        total_containers = sum(
            x.quantity for x in self.shipment.load_details.all()
        )

        handling = Decimal("0")
        previous_mode = None

        for segment in self.shipment.segments.all().order_by("sequence_no"):
            current_mode = segment.transport_mode

            if previous_mode:
                if current_mode == "OCEAN":
                    handling += Decimal(total_containers * 5)
                elif current_mode == "RAIL":
                    handling += Decimal(total_containers * 3)
                elif current_mode == "ROAD":
                    handling += Decimal(total_containers * 1)
                elif current_mode == "INLAND_WATERWAY":
                    handling += Decimal(total_containers * 5)

            previous_mode = current_mode

        # FIX: clamp to DB-safe range
        return clamp_decimal(handling)

    def calculate(self):
        cargo_weight = self.get_total_cargo_weight()
        container_adj = self.get_container_adjustment()
        load_factor = self.get_load_factor(cargo_weight)

        total_transport = Decimal("0")
        segment_results = []

        for segment in self.shipment.segments.all().order_by("sequence_no"):
            # FIX: was instantiating EmissionCalculationService with wrong
            # signature (shipment=…). Now passes the correct keyword args.
            result = EmissionCalculationService(
                segment=segment,
                cargo_weight=cargo_weight,
                container_adjustment=container_adj,
                load_factor=load_factor,
            ).calculate()

            co2e_decimal = clamp_decimal(Decimal(str(result["co2e_kg"])))

            # Persist per-segment values safely
            segment.segment_emission_kg = float(co2e_decimal)
            segment.distance_km = result["distance_km"]
            segment.emission_factor = result["emission_factor_g_per_tkm"]
            segment.route_type = result["route_type"]
            segment.save(update_fields=[
                "segment_emission_kg",
                "distance_km",
                "emission_factor",
                "route_type",
            ])

            # Overwrite co2e_kg in result with clamped value so caller is safe
            result["co2e_kg"] = float(co2e_decimal)
            segment_results.append(result)
            total_transport += co2e_decimal

        handling_emission = self.calculate_handling_emission()
        grand_total = clamp_decimal(total_transport + handling_emission)

        return {
            "cargo_weight": float(cargo_weight),
            "container_adjustment": float(container_adj),
            "load_factor": float(load_factor),
            "segments": segment_results,
            "transport_emission": round(float(total_transport), 3),
            "handling_emission": round(float(handling_emission), 3),
            "grand_total": round(float(grand_total), 3),
        }


# ---------------------------------------------------------------------------
# BaseCalculator + mode-specific calculators
# ---------------------------------------------------------------------------

class BaseCalculator:

    def __init__(self, segment, cargo_weight, container_adjustment, load_factor):
        self.segment = segment
        self.cargo_weight = Decimal(str(cargo_weight))
        self.container_adjustment = Decimal(str(container_adjustment))
        self.load_factor = Decimal(str(load_factor))

    def build_response(self, route_type: str, distance: float, emission_factor: float) -> dict:
        """
        co2e_kg = (distance * weight_t * g_per_tkm * container_adj * load_factor) / 1000
        FIX: clamp result to DB-safe range before returning.
        """
        co2e = (
                       Decimal(str(distance))
                       * self.cargo_weight
                       * Decimal(str(emission_factor))
                       * self.container_adjustment
                       * self.load_factor
               ) / Decimal("1000")

        co2e = clamp_decimal(co2e)

        return {
            "transport_mode": self.segment.transport_mode,
            "route_type": route_type,
            "distance_km": round(float(distance), 3),
            "cargo_weight_t": float(self.cargo_weight),
            "emission_factor_g_per_tkm": float(emission_factor),
            "container_adjustment": float(self.container_adjustment),
            "load_factor": float(self.load_factor),
            "co2e_kg": round(float(co2e), 3),
        }


class OceanCalculator(BaseCalculator):
    EMISSION_FACTORS = {
        "CONTAINER_VESSEL": 15.0,
        "BULK_CARRIER": 7.0,
        "RORO": 30.0,
        "FEEDER_VESSEL": 22.0,
    }

    def calculate(self):
        origin = self.segment.origin_location
        destination = self.segment.destination_location

        route = sr.searoute(
            [float(origin.longitude), float(origin.latitude)],
            [float(destination.longitude), float(destination.latitude)],
        )
        distance = route.properties["length"]
        emission_factor = self.EMISSION_FACTORS.get(self.segment.vessel_type, 15.0)

        return self.build_response(
            route_type="MARITIME",
            distance=distance,
            emission_factor=emission_factor,
        )


class InlandWaterwayCalculator(BaseCalculator):

    def calculate(self):
        route_type = getattr(self.segment, "route_type", None) or "COASTAL_SEA"
        distance = float(self.segment.distance_km)
        emission_factor = 20.0 if route_type == "COASTAL_SEA" else 14.0

        return self.build_response(
            route_type=route_type,
            distance=distance,
            emission_factor=emission_factor,
        )


class RailCalculator(BaseCalculator):
    EMISSION_FACTORS = {
        "ELECTRIC": 22.0,
        "DIESEL": 35.0,
        "DEFAULT": 30.0,
    }

    def calculate(self):
        traction = getattr(self.segment, "traction", "DEFAULT")
        distance = float(self.segment.distance_km)
        emission_factor = self.EMISSION_FACTORS.get(traction, 30.0)

        return self.build_response(
            route_type="RAIL",
            distance=distance,
            emission_factor=emission_factor,
        )


class RoadCalculator(BaseCalculator):
    EMISSION_FACTORS = {
        "HEAVY": 120.0,
        "MEDIUM": 150.0,
        "LIGHT": 210.0,
    }

    def calculate(self):
        vehicle_type = getattr(self.segment, "vehicle_type", "HEAVY")
        distance = float(self.segment.distance_km)
        emission_factor = self.EMISSION_FACTORS.get(vehicle_type, 120.0)

        return self.build_response(
            route_type="ROAD",
            distance=distance,
            emission_factor=emission_factor,
        )


class AirCalculator(BaseCalculator):
    EMISSION_FACTORS = {
        "PASSENGER_BELLY": 602.0,
        "FREIGHTER": 750.0,
    }

    def calculate(self):
        aircraft_type = getattr(self.segment, "aircraft_type", "FREIGHTER")
        distance = float(self.segment.distance_km)
        emission_factor = self.EMISSION_FACTORS.get(aircraft_type, 750.0)

        return self.build_response(
            route_type="AIR",
            distance=distance,
            emission_factor=emission_factor,
        )


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

import requests


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

    return data["routes"][0]["distance"] / 1000  # metres → km


def calculate_distance(segment) -> float:
    origin_lat = float(segment.origin_location.latitude)
    origin_lon = float(segment.origin_location.longitude)
    dest_lat = float(segment.destination_location.latitude)
    dest_lon = float(segment.destination_location.longitude)

    origin = (origin_lat, origin_lon)
    destination = (dest_lat, dest_lon)

    mode = segment.transportation_mode

    if mode == 5:  # Ocean
        route = sr.searoute(
            [origin_lon, origin_lat],
            [dest_lon, dest_lat],
        )
        return route["properties"]["length"]

    elif mode == 10:  # Air
        return haversine(origin, destination)

    elif mode == 15:  # Road
        return calculate_road_distance(origin_lat, origin_lon, dest_lat, dest_lon)

    elif mode == 20:  # Rail — straight-line * detour factor
        return haversine(origin, destination) * 1.15

    return 0.0
