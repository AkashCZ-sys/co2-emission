from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from tenants.context import get_current_tenant
from tenants.permissions import IsTenantAuthenticated
from .serializers import ShipmentEmissionRequestSerializer
from .models import Segment
from .utility import (
    haversine_distance_km,
    calculate_distance_based_emission,
    calculate_fuel_based_emission,
    resolve_calculation_method,
    resolve_shipment_method,
    CONTAINER_ADJUSTMENTS,
)


@extend_schema(request=ShipmentEmissionRequestSerializer, responses={200: dict})
class ShipmentEmissionCalculateView(APIView):
    permission_classes = [IsTenantAuthenticated]   # ← explicit per-view

    def post(self, request, *args, **kwargs):
        serializer = ShipmentEmissionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # tenant is guaranteed non-None here because:
        # 1. TenantMiddleware ran and set thread-local
        # 2. IsTenantAuthenticated confirmed user.tenant == request.tenant
        tenant = get_current_tenant()

        if tenant is None:
            # Defensive fallback — should never reach here
            return Response(
                {"detail": "Tenant context missing. Include X-Tenant-ID header."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consider_handling: bool = data["consider_handling_emission"]

        container_adjustment_factor: float = 1.0
        for load in data.get("load_details", []):
            ct = (load.get("container_type") or "").upper()
            if ct in CONTAINER_ADJUSTMENTS:
                container_adjustment_factor = CONTAINER_ADJUSTMENTS[ct]
                break

        total_cargo_weight: float = sum(
            ld["weight_in_tonne"] for ld in data.get("load_details", [])
        )
        load_factor: float = 1.0

        segments_response = []
        segment_methods_used = []
        shipment_total_co2: float = 0.0
        shipment_total_tkm: float = 0.0

        for idx, seg_input in enumerate(data["journey_segments"], start=1):

            calc_method = resolve_calculation_method(seg_input)

            sequence_number = seg_input.get("sequence_number") or idx
            external_ref    = seg_input.get("external_segment_ref") or ""
            transport_mode  = seg_input["transport_mode"]
            freight_type    = seg_input.get("freight_type") or ""

            o_lat = float(seg_input["origin_coordinates"]["latitude"])
            o_lon = float(seg_input["origin_coordinates"]["longitude"])
            d_lat = float(seg_input["destination_coordinates"]["latitude"])
            d_lon = float(seg_input["destination_coordinates"]["longitude"])

            straight_line_km = haversine_distance_km(o_lat, o_lon, d_lat, d_lon)

            segment = Segment.objects.create(
                tenant=tenant,
                external_segment_ref=external_ref,
                sequence_number=sequence_number,
                transport_mode=transport_mode,
                freight_type=freight_type or None,
                origin_latitude=o_lat,
                origin_longitude=o_lon,
                destination_latitude=d_lat,
                destination_longitude=d_lon,
                distance_km=straight_line_km,
                fuel_type=seg_input.get("fuel_type") or None,
                fuel_amount=seg_input.get("fuel_amount"),
                fuel_amount_unit=seg_input.get("fuel_amount_unit") or None,
                total_payload_tonne=seg_input.get("total_payload_tonne"),
                consider_handling_emission=consider_handling,
            )

            if calc_method == "FUEL_BASED":
                emission = calculate_fuel_based_emission(
                    segment=segment,
                    cargo_weight_tonne=total_cargo_weight,
                    tenant=tenant,
                )
            else:
                emission = calculate_distance_based_emission(
                    segment=segment,
                    cargo_weight_tonne=total_cargo_weight,
                    container_adjustment_factor=container_adjustment_factor,
                    load_factor=load_factor,
                    tenant=tenant,
                )

            shipment_total_co2 += emission.co2_kg
            shipment_total_tkm += emission.activity_tonne_km
            segment_methods_used.append(calc_method)

            segments_response.append({
                "external_segment_ref": segment.external_segment_ref,
                "sequence_number":      segment.sequence_number,
                "transport_mode":       segment.transport_mode,
                "freight_type":         segment.freight_type,
                "distance_km":          emission.distance_km,
                "cargo_weight_tonne":   emission.cargo_weight_tonne,
                "activity_tonne_km":    emission.activity_tonne_km,
                "allocation_share":     emission.allocation_share,
                "co2_kg":               emission.co2_kg,
                "calculation_method":   calc_method,
            })

        response_data = {
            "shipment": {
                "tenant_id":                  str(tenant.id),
                "total_cargo_weight_tonne":   total_cargo_weight,
                "calculation_method":         resolve_shipment_method(segment_methods_used),
                "consider_handling_emission": consider_handling,
                "total_co2_kg":               round(shipment_total_co2, 3),
                "total_activity_tonne_km":    round(shipment_total_tkm, 3),
                "segment_count":              len(segments_response),
            },
            "segments": segments_response,
        }
        return Response(response_data, status=status.HTTP_200_OK)