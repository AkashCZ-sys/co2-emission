import datetime
import re
import uuid
from decimal import Decimal
from enum import Enum

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


EMISSION_FACTORS = {
    FuelTypeEnum.DIESEL.CODE: Decimal("2.68"),
    FuelTypeEnum.LNG.CODE: Decimal("2.75"),
    FuelTypeEnum.HFO.CODE: Decimal("3.114"),
    FuelTypeEnum.VLSFO.CODE: Decimal("3.151"),
    FuelTypeEnum.JET_FUEL.CODE: Decimal("2.54"),
    FuelTypeEnum.ELECTRIC.CODE: Decimal("0.0"),
}

from decimal import Decimal

ROAD_FACTORS = {
    "HEAVY_TRUCK": Decimal("62"),
    "MEDIUM_TRUCK": Decimal("83"),
    "LIGHT_TRUCK": Decimal("151"),
}

RAIL_FACTORS = {
    "ELECTRIC": Decimal("6"),
    "DIESEL": Decimal("22"),
}

AIR_FACTORS = {
    "FREIGHTER": Decimal("602"),
    "BELLY": Decimal("520"),
}

OCEAN_FACTORS = {
    "CONTAINER_VESSEL": Decimal("16"),
    "BULK_CARRIER": Decimal("7"),
    "FEEDER_VESSEL": Decimal("21"),
}

CONTAINER_ADJUSTMENTS = {
    "20_FOOT": Decimal("1.0"),
    "40_FOOT": Decimal("0.85"),
    "REEFER": Decimal("1.35"),
    "ISO_TANK": Decimal("1.20"),
}

HANDLING_FACTOR = Decimal("0.003")


def get_emission_factor(fuel_type):
    return EMISSION_FACTORS.get(fuel_type, Decimal("0.0"))


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
    """
    Try to parse date from multiple formats.
    Returns date or None.
    """
    if not isinstance(value, str):
        return None

    value = value.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def parse_year_month(value: str):
    """
    Parses:
    - YYYY/MM or YYYY-MM
    - MM/YYYY or MM-YYYY
    - MM/YY or MM-YY

    Returns (year, month) or None
    """
    value = value.strip()

    # YYYY/MM or YYYY-MM
    match_ym = re.match(r"^(\d{4})[\/\-](\d{1,2})$", value)
    if match_ym:
        year, month = int(match_ym.group(1)), int(match_ym.group(2))
        if 1 <= month <= 12:
            return year, month
        return None

    # MM/YYYY or MM-YYYY
    match_my4 = re.match(r"^(\d{1,2})[\/\-](\d{4})$", value)
    if match_my4:
        month, year = int(match_my4.group(1)), int(match_my4.group(2))
        if 1 <= month <= 12:
            return year, month
        return None

    # MM/YY or MM-YY
    match_my2 = re.match(r"^(\d{1,2})[\/\-](\d{2})$", value)
    if match_my2:
        month, year = int(match_my2.group(1)), int(match_my2.group(2))
        if 1 <= month <= 12:
            return 2000 + year, month
        return None

    return None


def parse_day_month(value: str):
    """
    Parses:
    - DD/MM
    - DD-MM

    Returns (month, day) or None
    """
    value = value.strip()

    match = re.match(r"^(\d{1,2})[\/\-](\d{1,2})$", value)
    if not match:
        return None

    day, month = int(match.group(1)), int(match.group(2))

    if 1 <= day <= 31 and 1 <= month <= 12:
        return month, day

    return None


def get_custom_folder_path(document_type_id, is_temporary, data_dict: dict, application_name,
                           le_id=None, document_type_name=""):
    folder_path = []

    # Append the current date in YYYY/MM/DD format
    current_date = datetime.now().strftime(DATE_FOLDER_FORMAT)

    folder_path.append(current_date)

    return "/".join(folder_path)


# class ShipmentStatusEnum(BaseEnum):
#     DRAFT = (5, "Draft")
#     BOOKED = (10, "Booked")
#     CONFIRMED = (15, "Confirmed")
#     SHIPPED = (25, "Shipped")
#     MODIFIED = (20, "Modified")
#     CANCELLED = (30, "Cancelled")
#

class TransportModeEnum(BaseEnum):
    OCEAN = (5, "Ocean")
    AIR = (10, "Air")
    Road = (15, "Road")
    RAIL = (20, "Rail")


class ServiceTypeEnum(BaseEnum):
    CY = (5, "CY")
    CFS = (10, 'CFS')


class CargoTypeEnum(BaseEnum):
    NORMAL = (5, "Normal")
    REEFER = (10, "Reefer")
    DG = (15, "Dangerous Goods")


# class CompanyTypeEnum(BaseEnum):
#     """
#     Enum representing the type of logistics company:
#     """
#     VENDOR = (5, "Vendor")
#     ORIGIN_AGENT = (10, "Origin_agent")
#     DESTINATION_AGENT = (15, "Destination_agent")
#     CUSTOMER = (20, "Customer")
#     SUPPLIER = (25, "Supplier")


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


#
# class PaymentTermsEnum(BaseEnum):
#     PREPAID = (5, "Prepaid")
#     COLLECT = (10, "Collect")

def enum_search_q(enum_cls, field_name, search_value):
    """
    Builds a Q() object for enum name/description search.
    """
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

    # ---------------- TEXT SEARCH ----------------
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

    # ---------------- ENUM SEARCH ----------------
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

    # ---------------- FLOAT SEARCH (EXACT) ----------------
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

    # ---------------- INTEGER SEARCH ----------------
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

        if search_value.isdigit() and len(search_value) == 2:
            int_value = int(search_value)

            # Month: 01–12
            if 1 <= int_value <= 12:
                q |= Q(created_on__month=int_value)
                q |= Q(cargo_readiness_date__month=int_value)

            # Day: 01–31
            if 1 <= int_value <= 31:
                q |= Q(created_on__day=int_value)
                q |= Q(cargo_readiness_date__day=int_value)

    # ---------------- YEAR-MONTH ----------------
    ym = parse_year_month(search_value)
    if ym:
        if ym:
            year, month = ym
            q |= Q(created_on__year=year, created_on__month=month)
            q |= Q(cargo_readiness_date__year=year, cargo_readiness_date__month=month)

    # ---------------- DAY-MONTH (DD/MM) ----------------
    dm = parse_day_month(search_value)
    if dm:
        month, day = dm
        q |= Q(created_on__month=month, created_on__day=day)
        q |= Q(cargo_readiness_date__month=month, cargo_readiness_date__day=day)

    # ---------------- FULL DATE ----------------
    try:
        parsed_date = parse_search_date(search_value)
        q |= Q(created_on__date=parsed_date)
        q |= Q(cargo_readiness_date__date=parsed_date)
    except ValueError:
        pass

    # ---------------- BOOLEAN ----------------
    if search_lower in ("active", "true"):
        q |= Q(is_active=True)
    elif search_lower in ("inactive", "false"):
        q |= Q(is_active=False)

    return q


def apply_fk_filter(queryset, field, value):
    """
    field = FK field name on ShipmentOrder
    value = id OR name
    """
    if not value:
        return queryset

    # ID filter
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return queryset.filter(**{f"{field}_id": int(value)})

    # Name filter
    return queryset.filter(**{f"{field}__name__icontains": value})


def generate_booking_id():
    """Generates a unique booking ID."""
    return f"VBK-{uuid.uuid4().hex[:8].upper()}"
    # return 'vbk223311'


def calculate_handling_emission(self):
    if not self.shipment.consider_handling_emission:
        return 0

    total_containers = sum(
        x.quantity
        for x in self.shipment.load_details.all()
    )

    handling = 0

    segments = (
        self.shipment.segments
        .all()
        .order_by("sequence_no")
    )

    previous_mode = None

    for segment in segments:

        current_mode = (
            segment.transport_mode
        )

        if previous_mode:

            if current_mode == "OCEAN":
                handling += (
                        total_containers * 5
                )

            elif current_mode == "RAIL":
                handling += (
                        total_containers * 3
                )

            elif current_mode == "ROAD":
                handling += (
                        total_containers * 1
                )

            elif current_mode == (
                    "INLAND_WATERWAY"
            ):
                handling += (
                        total_containers * 5
                )

        previous_mode = current_mode

    return handling


def get_load_factor(self, cargo_weight):
    if (self.shipment.container_load_type == "FCL"):
        return 1.0
    capacity = 40
    factor = cargo_weight / capacity
    return max(0.1, min(factor, 1.0))


def get_container_adjustment(self):
    total_quantity = 0
    weighted_sum = 0

    for load in self.shipment.load_details.all():
        weighted_sum += (
                load.container_adjustment_factor
                * load.quantity
        )

        total_quantity += load.quantity

    if total_quantity == 0:
        return 1

    return weighted_sum / total_quantity


def get_total_cargo_weight(self):
    total_weight = 0

    for load in self.shipment.load_details.all():
        total_weight += (
                load.weight_tonne
                * load.quantity
        )

    return total_weight


class ShipmentEmissionCalculator:

    def __init__(self, shipment):
        self.shipment = shipment

    def get_total_cargo_weight(self):
        total_weight = Decimal("0")

        for load in self.shipment.load_details.all():
            total_weight += (
                    Decimal(load.weight_tonne)
                    * load.quantity
            )

        return total_weight

    def get_container_adjustment(self):

        total_quantity = 0
        weighted_sum = Decimal("0")

        for load in self.shipment.load_details.all():
            weighted_sum += (
                    Decimal(load.container_adjustment_factor)
                    * load.quantity
            )

            total_quantity += load.quantity

        if total_quantity == 0:
            return Decimal("1")

        return weighted_sum / total_quantity

    def get_load_factor(self, cargo_weight):

        if self.shipment.container_load_type == "FCL":
            return Decimal("1")

        capacity = Decimal("40")

        factor = cargo_weight / capacity

        return max(
            Decimal("0.1"),
            min(factor, Decimal("1"))
        )

    def calculate_handling_emission(self):

        if not self.shipment.consider_handling_emission:
            return Decimal("0")

        total_containers = sum(
            x.quantity
            for x in self.shipment.load_details.all()
        )

        handling = Decimal("0")

        segments = (
            self.shipment.segments
            .all()
            .order_by("sequence_no")
        )

        previous_mode = None

        for segment in segments:

            current_mode = segment.transport_mode

            if previous_mode:

                if current_mode == "OCEAN":
                    handling += Decimal(
                        total_containers * 5
                    )

                elif current_mode == "RAIL":
                    handling += Decimal(
                        total_containers * 3
                    )

                elif current_mode == "ROAD":
                    handling += Decimal(
                        total_containers * 1
                    )

                elif current_mode == "INLAND_WATERWAY":
                    handling += Decimal(
                        total_containers * 5
                    )

            previous_mode = current_mode

        return handling

    def calculate(self):

        cargo_weight = (
            self.get_total_cargo_weight()
        )

        container_adj = (
            self.get_container_adjustment()
        )

        load_factor = (
            self.get_load_factor(
                cargo_weight
            )
        )

        total_transport_emission = Decimal("0")

        segment_results = []

        segments = (
            self.shipment.segments
            .all()
            .order_by("sequence_no")
        )

        for segment in segments:
            result = SegmentEmissionCalculator(
                segment=segment,
                cargo_weight=cargo_weight,
                container_adjustment=container_adj,
                load_factor=load_factor
            ).calculate()

            segment.segment_emission_kg = result[
                "co2e_kg"
            ]

            segment.distance_km = result[
                "distance_km"
            ]

            segment.emission_factor = result[
                "emission_factor_g_per_tkm"
            ]

            segment.route_type = result[
                "route_type"
            ]

            segment.save(
                update_fields=[
                    "segment_emission_kg",
                    "distance_km",
                    "emission_factor",
                    "route_type"
                ]
            )

            segment_results.append(result)

            total_transport_emission += Decimal(
                str(result["co2e_kg"])
            )

        handling_emission = (
            self.calculate_handling_emission()
        )

        grand_total = (
                total_transport_emission
                + handling_emission
        )

        return {
            "cargo_weight": float(cargo_weight),
            "container_adjustment":
                float(container_adj),
            "load_factor":
                float(load_factor),
            "segments":
                segment_results,
            "transport_emission":
                round(
                    float(
                        total_transport_emission
                    ),
                    3
                ),
            "handling_emission":
                round(
                    float(
                        handling_emission
                    ),
                    3
                ),
            "grand_total":
                round(
                    float(
                        grand_total
                    ),
                    3
                )
        }


from decimal import Decimal


class BaseCalculator:

    def __init__(
            self,
            segment,
            cargo_weight,
            container_adjustment,
            load_factor
    ):
        self.segment = segment
        self.cargo_weight = Decimal(str(cargo_weight))
        self.container_adjustment = Decimal(
            str(container_adjustment)
        )
        self.load_factor = Decimal(
            str(load_factor)
        )

    def build_response(
            self,
            route_type,
            distance,
            emission_factor
    ):
        co2e = (
                       Decimal(str(distance))
                       * self.cargo_weight
                       * Decimal(str(emission_factor))
                       * self.container_adjustment
                       * self.load_factor
               ) / Decimal("1000")

        return {
            "transport_mode":
                self.segment.transport_mode,

            "route_type":
                route_type,

            "distance_km":
                round(float(distance), 3),

            "cargo_weight_t":
                float(self.cargo_weight),

            "emission_factor_g_per_tkm":
                float(emission_factor),

            "container_adjustment":
                float(
                    self.container_adjustment
                ),

            "load_factor":
                float(
                    self.load_factor
                ),

            "co2e_kg":
                round(float(co2e), 3)
        }


class OceanCalculator(BaseCalculator):
    EMISSION_FACTORS = {
        "CONTAINER_VESSEL": 15,
        "BULK_CARRIER": 7,
        "RORO": 30,
        "FEEDER_VESSEL": 22
    }

    def calculate(self):
        distance = (
            self.segment.distance_km
        )

        emission_factor = (
            self.EMISSION_FACTORS.get(
                self.segment.vessel_type,
                15
            )
        )

        return self.build_response(
            route_type="MARITIME",
            distance=distance,
            emission_factor=emission_factor
        )


class InlandWaterwayCalculator(
    BaseCalculator
):

    def calculate(self):
        route_type = (
                self.segment.route_type
                or "COASTAL_SEA"
        )

        distance = (
            self.segment.distance_km
        )

        emission_factor = (
            20
            if route_type == "COASTAL_SEA"
            else 14
        )

        return self.build_response(
            route_type=route_type,
            distance=distance,
            emission_factor=emission_factor
        )


class RailCalculator(
    BaseCalculator
):
    EMISSION_FACTORS = {
        "ELECTRIC": 22,
        "DIESEL": 35,
        "DEFAULT": 30
    }

    def calculate(self):
        traction = getattr(
            self.segment,
            "traction",
            "DEFAULT"
        )

        distance = (
            self.segment.distance_km
        )

        emission_factor = (
            self.EMISSION_FACTORS.get(
                traction,
                30
            )
        )

        return self.build_response(
            route_type="RAIL",
            distance=distance,
            emission_factor=emission_factor
        )


class RoadCalculator(
    BaseCalculator
):
    EMISSION_FACTORS = {
        "HEAVY": 120,
        "MEDIUM": 150,
        "LIGHT": 210
    }

    def calculate(self):
        vehicle_type = getattr(
            self.segment,
            "vehicle_type",
            "HEAVY"
        )

        distance = (
            self.segment.distance_km
        )

        emission_factor = (
            self.EMISSION_FACTORS.get(
                vehicle_type,
                120
            )
        )

        return self.build_response(
            route_type="ROAD",
            distance=distance,
            emission_factor=emission_factor
        )


class AirCalculator(
    BaseCalculator
):
    EMISSION_FACTORS = {
        "PASSENGER_BELLY": 602,
        "FREIGHTER": 750
    }

    def calculate(self):
        aircraft_type = getattr(
            self.segment,
            "aircraft_type",
            "FREIGHTER"
        )

        distance = (
            self.segment.distance_km
        )

        emission_factor = (
            self.EMISSION_FACTORS.get(
                aircraft_type,
                750
            )
        )

        return self.build_response(
            route_type="AIR",
            distance=distance,
            emission_factor=emission_factor
        )


# class SegmentEmissionCalculator:
#     CALCULATORS = {
#         "OCEAN": OceanCalculator,
#         "ROAD": RoadCalculator,
#         "RAIL": RailCalculator,
#         "AIR": AirCalculator,
#         "INLAND_WATERWAY":
#             InlandWaterwayCalculator
#     }
#
#     def calculate(self):
#         calculator_cls = (
#             self.CALCULATORS[
#                 self.segment.transport_mode
#             ]
#         )
#
#         calculator = calculator_cls(
#             segment=self.segment,
#             cargo_weight=self.cargo_weight,
#             container_adjustment=
#             self.container_adjustment,
#             load_factor=self.load_factor
#         )
#
#         return calculator.calculate()
from haversine import haversine
import searoute as sr


def calculate_distance(segment):
    origin = (
        float(segment.origin_location.latitude),
        float(segment.origin_location.longitude)
    )

    destination = (
        float(segment.destination_location.latitude),
        float(segment.destination_location.longitude)
    )

    transport_mode = segment.transportation_mode

    if transport_mode == 5:
        route = sr.searoute(
            origin[::-1],
            destination[::-1]
        )

        return route['properties']['length']

    return haversine(origin, destination)


class EmissionCalculationService:

    def __init__(self, shipment):
        self.shipment = shipment

    def get_total_weight(self):

        total = Decimal("0")

        for load in self.shipment.load_details.all():
            total += (
                    load.weight_in_tonne
                    * load.quantity
            )

        return total

    def get_container_adjustment(self):

        dominant = (
            self.shipment.load_details.first()
        )

        if not dominant:
            return Decimal("1")

        return CONTAINER_ADJUSTMENTS.get(
            dominant.container_type,
            Decimal("1")
        )

    def get_emission_factor(self, segment):

        mode = segment.transportation_mode

        if mode == 5:

            return OCEAN_FACTORS.get(
                segment.freight_type,
                Decimal("16")
            )

        elif mode == 10:

            return AIR_FACTORS.get(
                segment.freight_type,
                Decimal("602")
            )

        elif mode == 15:

            return ROAD_FACTORS.get(
                segment.freight_type,
                Decimal("62")
            )

        elif mode == 20:

            return RAIL_FACTORS.get(
                segment.freight_type,
                Decimal("22")
            )

        return Decimal("0")

    def calculate_segment_emission(
            self,
            segment,
            distance
    ):

        cargo_weight = (
            self.get_total_weight()
        )

        emission_factor = (
            self.get_emission_factor(segment)
        )

        adjustment = (
            self.get_container_adjustment()
        )

        transport_emission = (
                                     distance
                                     * cargo_weight
                                     * emission_factor
                                     * adjustment
                             ) / Decimal("1000")

        handling = Decimal("0")

        if (
                self.shipment.consider_handling_emission
                and segment.transportation_mode == 5
        ):
            handling = (
                    cargo_weight
                    * distance
                    * HANDLING_FACTOR
            )

        total = (
                transport_emission
                + handling
        )

        return {
            "cargo_weight": cargo_weight,
            "transport_emission": transport_emission,
            "handling_emission": handling,
            "total": total,
            "distance": distance,
            "factor": emission_factor,
            "adjustment": adjustment,
        }
