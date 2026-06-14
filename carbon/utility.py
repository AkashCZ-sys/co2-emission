from typing import Optional, Dict, Tuple

import requests
import searoute as sr
from haversine import haversine

from .models import Segment, SegmentEmission

# ---------------------------------------------------------------------------
# Transport mode constants
# ---------------------------------------------------------------------------

TRANSPORT_MODE_OCEAN = "OCEAN"
TRANSPORT_MODE_AIR = "AIR"
TRANSPORT_MODE_ROAD = "ROAD"
TRANSPORT_MODE_RAIL = "RAIL"

# ---------------------------------------------------------------------------
# Distance-based emission factors (g CO2e per tonne-km)
#
# These values come from empirical studies / databases (e.g. GLEC, national
# inventories).  In production, replace with a DB or an external factor API.
# ---------------------------------------------------------------------------

ROAD_FACTORS_G_PER_TKM: Dict[str, float] = {
    "HEAVY": 62.0,
    "MEDIUM": 83.0,
    "LIGHT": 151.0,
}

RAIL_FACTORS_G_PER_TKM: Dict[str, float] = {
    "ELECTRIC": 6.0,
    "DIESEL": 22.0,
    "DEFAULT": 30.0,
}

AIR_FACTORS_G_PER_TKM: Dict[str, float] = {
    "FREIGHTER": 750.0,
    "PASSENGER_BELLY": 602.0,
}

OCEAN_FACTORS_G_PER_TKM: Dict[str, float] = {
    "CONTAINER_VESSEL": 16.0,
    "BULK_CARRIER": 7.0,
    "RORO": 30.0,
    "FEEDER_VESSEL": 22.0,
}

# Container-type adjustment multipliers
CONTAINER_ADJUSTMENTS: Dict[str, float] = {
    "20_FOOT": 1.0,
    "40_FOOT": 0.85,
    "REEFER": 1.35,
    "ISO_TANK": 1.20,
}

# Extra emissions per tonne-km for port/terminal handling (ocean only)
HANDLING_FACTOR: float = 0.003

MAX_FLOAT_VALUE: float = float("9999999999.99")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clamp_float(value: float) -> float:
    """Clamp a float to ±MAX_FLOAT_VALUE to guard against DB overflow."""
    if value > MAX_FLOAT_VALUE:
        return MAX_FLOAT_VALUE
    if value < -MAX_FLOAT_VALUE:
        return -MAX_FLOAT_VALUE
    return value


# ---------------------------------------------------------------------------
# Distance calculation helpers
# ---------------------------------------------------------------------------

def calculate_sea_distance(
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
) -> float:
    """
    Use the *searoute* library to compute a realistic sea-route distance (km).
    Note: searoute expects (lon, lat) order.
    """
    route = sr.searoute(
        [float(origin_lon), float(origin_lat)],
        [float(destination_lon), float(destination_lat)],
    )
    return float(route.properties["length"])


def calculate_road_distance(
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
) -> float:
    """
    Use the public OSRM routing API to get a realistic driving distance,
    then convert metres → kilometres.
    """
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
        raise ValueError("No road route found between the supplied coordinates.")
    return data["routes"][0]["distance"] / 1000.0


def haversine_distance_km(
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
) -> float:
    """
    Straight-line (great-circle) distance in km using the Haversine formula.
    Used as the default / fallback distance calculation.
    """
    origin = (float(origin_lat), float(origin_lon))
    destination = (float(destination_lat), float(destination_lon))
    return haversine(origin, destination)


def calculate_segment_distance(segment: Segment) -> float:
    """
    Return distance_km for *segment* based on its transport_mode.

    - OCEAN  → sea-route via searoute
    - AIR    → great-circle (haversine)
    - ROAD   → driving distance via OSRM
    - RAIL   → haversine × 1.15 detour factor
    - Other  → 0.0
    """
    origin_lat = float(segment.origin_latitude)
    origin_lon = float(segment.origin_longitude)
    dest_lat = float(segment.destination_latitude)
    dest_lon = float(segment.destination_longitude)

    origin = (origin_lat, origin_lon)
    destination = (dest_lat, dest_lon)
    mode = (segment.transport_mode or "").upper()

    if mode == TRANSPORT_MODE_OCEAN:
        return calculate_sea_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    if mode == TRANSPORT_MODE_AIR:
        return haversine(origin, destination)
    if mode == TRANSPORT_MODE_ROAD:
        return calculate_road_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    if mode == TRANSPORT_MODE_RAIL:
        return haversine(origin, destination) * 1.15

    return 0.0


# ---------------------------------------------------------------------------
# Distance-based emission factor lookup
# ---------------------------------------------------------------------------

def get_distance_factor_for_segment(segment: Segment) -> float:
    """
    Return the distance-based emission factor (g CO2e / tonne-km) for *segment*
    based on its transport_mode and freight_type.  Defaults are applied when
    freight_type is absent.
    """
    mode = (segment.transport_mode or "").upper()
    freight_type = (segment.freight_type or "").upper() or None

    if mode == TRANSPORT_MODE_OCEAN:
        return OCEAN_FACTORS_G_PER_TKM.get(freight_type or "CONTAINER_VESSEL", 16.0)

    if mode == TRANSPORT_MODE_AIR:
        return AIR_FACTORS_G_PER_TKM.get(freight_type or "FREIGHTER", 750.0)

    if mode == TRANSPORT_MODE_ROAD:
        return ROAD_FACTORS_G_PER_TKM.get(freight_type or "HEAVY", 62.0)

    if mode == TRANSPORT_MODE_RAIL:
        return RAIL_FACTORS_G_PER_TKM.get(freight_type or "DEFAULT", 30.0)

    return 0.0


# ---------------------------------------------------------------------------
# Fuel-based emission factor computation (formula-driven)
#
# Formula:
#   EF_CO2 (kg CO2 / kg fuel) = carbon_content × (44 / 12)   [molar mass ratio]
#   EF_CO2 (kg CO2 / litre)   = EF_CO2_per_kg × density_kg_per_L
# ---------------------------------------------------------------------------

def _fuel_properties(fuel_type: str) -> Tuple[float, float]:
    """
    Return (carbon_content_kgC_per_kg_fuel, density_kg_per_litre) for *fuel_type*.

    Values are approximate IPCC / literature defaults.
    """
    ft = (fuel_type or "").upper()

    if ft == "DIESEL":
        return 0.86, 0.84
    if ft in ("HFO", "HEAVY FUEL OIL"):
        return 0.86, 0.98
    if ft in ("VLSFO", "VERY LOW SULFUR FUEL OIL"):
        return 0.85, 0.95
    if ft in ("JET_FUEL", "JET", "KEROSENE"):
        return 0.86, 0.80
    if ft in ("LNG", "LIQUEFIED NATURAL GAS"):
        return 0.75, 0.45
    if ft == "ELECTRIC":
        # No combustion CO2; upstream electricity emissions handled separately.
        return 0.0, 1.0

    raise ValueError(f"Unsupported fuel_type for formula-based factor: '{fuel_type}'")


def get_fuel_factor_kg_per_unit(fuel_type: str, unit: str) -> float:
    """
    Compute kg CO2 emitted per unit of *fuel_type* (tank-to-wheel).

    Steps:
      1. Retrieve carbon_content (kg C / kg fuel) and density (kg / L).
      2. kg CO2 / kg fuel = carbon_content × (44 / 12).
      3. kg CO2 / litre  = step-2 result × density.
    """
    u = (unit or "").upper()
    carbon_content, density_kg_per_l = _fuel_properties(fuel_type)

    co2_per_kg_fuel = carbon_content * (44.0 / 12.0)

    if u in ("KG", "KILOGRAM"):
        return co2_per_kg_fuel

    if u in ("L", "LITRE", "LITER"):
        return co2_per_kg_fuel * density_kg_per_l

    raise ValueError(
        f"Unsupported fuel_amount_unit='{unit}'. Supported values: 'kg', 'litre'."
    )


def resolve_calculation_method(segment_input: dict) -> str:
    required_fuel_fields = (
        segment_input.get("fuel_type"),
        segment_input.get("fuel_amount"),
        segment_input.get("fuel_amount_unit"),
        segment_input.get("total_payload_tonne"),
    )
    if all(v is not None and v != "" for v in required_fuel_fields):
        return "FUEL_BASED"
    return "DISTANCE_FACTOR"


def resolve_shipment_method(segment_methods: list) -> str:
    unique = set(segment_methods)
    if len(unique) == 1:
        return unique.pop()
    return "MIXED"


# ---------------------------------------------------------------------------
# Distance-based emission calculation
# ---------------------------------------------------------------------------
def calculate_distance_based_emission(
        *,
        segment: Segment,
        cargo_weight_tonne: float,
        container_adjustment_factor: float = 1.0,
        load_factor: float = 1.0,
        tenant=None,  # ← add this
        extra_metadata: Optional[Dict] = None,
) -> SegmentEmission:
    distance_km = float(segment.distance_km or 0.0) or calculate_segment_distance(segment)
    emission_factor_g_per_tkm = get_distance_factor_for_segment(segment)

    transport_emission = (
                                 distance_km
                                 * cargo_weight_tonne
                                 * emission_factor_g_per_tkm
                                 * container_adjustment_factor
                                 * load_factor
                         ) / 1000.0

    handling = 0.0
    if (
            segment.consider_handling_emission
            and (segment.transport_mode or "").upper() == TRANSPORT_MODE_OCEAN
    ):
        handling = cargo_weight_tonne * distance_km * HANDLING_FACTOR

    transport_emission = clamp_float(transport_emission)
    handling = clamp_float(handling)
    total_co2_kg = clamp_float(transport_emission + handling)
    activity_tkm = cargo_weight_tonne * distance_km

    emission, _ = SegmentEmission.objects.update_or_create(
        segment=segment,
        defaults={
            "tenant": tenant,  # ← add this
            "cargo_weight_tonne": cargo_weight_tonne,
            "distance_km": round(distance_km, 3),
            "activity_tonne_km": round(activity_tkm, 3),
            "allocation_share": 1.0,
            "co2_kg": round(total_co2_kg, 3),
            "calculation_method": "DISTANCE_FACTOR",
        },
    )
    return emission


def calculate_fuel_based_emission(
        *,
        segment: Segment,
        cargo_weight_tonne: float,
        tenant=None,  # ← add this
        extra_metadata: Optional[Dict] = None,
) -> SegmentEmission:
    missing = [
        field
        for field, value in [
            ("fuel_type", segment.fuel_type),
            ("fuel_amount", segment.fuel_amount),
            ("fuel_amount_unit", segment.fuel_amount_unit),
            ("total_payload_tonne", segment.total_payload_tonne),
            ("distance_km", segment.distance_km),
        ]
        if not value and value != 0
    ]
    if missing:
        raise ValueError(
            f"The following fields are required for fuel-based calculation: "
            f"{', '.join(missing)}"
        )

    distance_km = float(segment.distance_km)
    fuel_factor_kg_per_unit = get_fuel_factor_kg_per_unit(
        fuel_type=segment.fuel_type,
        unit=segment.fuel_amount_unit,
    )

    leg_co2_kg = float(segment.fuel_amount) * fuel_factor_kg_per_unit
    leg_activity_tkm = float(segment.total_payload_tonne) * distance_km
    cargo_activity_tkm = cargo_weight_tonne * distance_km

    allocation_share = (
        cargo_activity_tkm / leg_activity_tkm if leg_activity_tkm > 0 else 0.0
    )
    co2_kg = leg_co2_kg * allocation_share
    leg_co2_kg = clamp_float(leg_co2_kg)
    co2_kg = clamp_float(co2_kg)

    emission, _ = SegmentEmission.objects.update_or_create(
        segment=segment,
        defaults={
            "tenant": tenant,  # ← add this
            "cargo_weight_tonne": cargo_weight_tonne,
            "distance_km": round(distance_km, 3),
            "activity_tonne_km": round(cargo_activity_tkm, 3),
            "allocation_share": round(allocation_share, 6),
            "co2_kg": round(co2_kg, 3),
            "calculation_method": "FUEL_BASED",
        },
    )
    return emission


# carbon/utility.py  — add this function after the constants section

def resolve_calculation_method(segment_input: dict) -> str:
    """
    Determine the calculation method for a single segment based solely
    on the presence of all four fuel fields in the raw input dict.

    Returns "FUEL_BASED" only when fuel_type, fuel_amount,
    fuel_amount_unit, and total_payload_tonne are all non-null/non-empty.
    Otherwise returns "DISTANCE_FACTOR".
    """
    required_fuel_fields = (
        segment_input.get("fuel_type"),
        segment_input.get("fuel_amount"),
        segment_input.get("fuel_amount_unit"),
        segment_input.get("total_payload_tonne"),
    )
    # All four must be present and non-empty
    if all(v is not None and v != "" for v in required_fuel_fields):
        return "FUEL_BASED"
    return "DISTANCE_FACTOR"


def resolve_shipment_method(segment_methods: list[str]) -> str:
    """
    Roll up per-segment methods into a single shipment-level label.

    - All FUEL_BASED      → "FUEL_BASED"
    - All DISTANCE_FACTOR → "DISTANCE_FACTOR"
    - Mixed               → "MIXED"
    """
    unique = set(segment_methods)
    if len(unique) == 1:
        return unique.pop()
    return "MIXED"
