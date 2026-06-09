from django.db import transaction
from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView, get_object_or_404
from rest_framework.views import APIView

from shipment_management.models import ShipmentOrder, ShipmentSegment
from shipment_management.serializers import (
    ShipmentOrderCreateSerializer,
    ShipmentOrderReadSerializer,
    ShipmentReadSerializer,
    ShipmentFilterSerializer, ShipmentEmissionSummarySerializer,
)


class ShipmentOrderCreateAPIView(CreateAPIView):
    queryset = ShipmentOrder.objects.all()
    serializer_class = ShipmentOrderCreateSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shipment_order = serializer.save()

        shipment_order = (
            ShipmentOrder.objects
            .prefetch_related(
                "load_details",
                "segments__emission",
            )
            .get(pk=shipment_order.pk)
        )

        response_serializer = ShipmentOrderReadSerializer(shipment_order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

# views.py
#
# class ShipmentOrderCreateAPIView(CreateAPIView):
#     queryset = ShipmentOrder.objects.all()
#     serializer_class = ShipmentOrderCreateSerializer
#
#     @transaction.atomic
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         shipment_order = serializer.save()
#
#         # Re-fetch with all related data
#         shipment_order = (
#             ShipmentOrder.objects
#             .prefetch_related(
#                 "load_details",
#                 "segments__emission",
#             )
#             .get(pk=shipment_order.pk)
#         )
#
#         # Use the same serializer the emission-summary endpoint uses
#         response_serializer = ShipmentEmissionSummarySerializer(shipment_order)
#         return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ShipmentOrderRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    queryset = (
        ShipmentOrder.objects
        .prefetch_related("load_details", "segments__emission")
    )
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ShipmentOrderReadSerializer
        return ShipmentOrderCreateSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Delete and recreate child records on update
        instance.load_details.all().delete()
        instance.segments.all().delete()

        validated_data = serializer.validated_data
        load_details_data = validated_data.pop("load_details", [])
        segments_data = validated_data.pop("segments", [])

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        from shipment_management.models import ShipmentLoadDetail
        for ld in load_details_data:
            ld.pop("id", None)
            ShipmentLoadDetail.objects.create(shipment_order=instance, **ld)

        for seg in segments_data:
            seg.pop("id", None)
            ShipmentSegment.objects.create(shipment_order=instance, **seg)

        instance.refresh_from_db()

        from shipment_management.utility import ShipmentEmissionCalculator
        from decimal import Decimal
        emission_result = ShipmentEmissionCalculator(instance).calculate()

        total_distance = sum(s["distance_km"] for s in emission_result["segments"])
        instance.total_weight_in_tonne = Decimal(str(emission_result["cargo_weight"]))
        instance.total_co2_kg = Decimal(str(emission_result["grand_total"]))
        instance.total_distance_km = Decimal(str(round(total_distance, 2)))
        instance.save(update_fields=["total_weight_in_tonne", "total_distance_km", "total_co2_kg"])

        instance = (
            ShipmentOrder.objects
            .prefetch_related("load_details", "segments__emission")
            .get(pk=instance.pk)
        )
        return Response(ShipmentOrderReadSerializer(instance).data)


class ShipmentFilterAPIView(APIView):
    serializer_class = ShipmentReadSerializer

    @extend_schema(request=ShipmentFilterSerializer, responses=ShipmentReadSerializer)
    def post(self, request):
        serializer = ShipmentFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        filter_map = {
            "shipment_number": "shipment_number",
            "cargo_type": "cargo_type",
            "cargo_temperature_type": "cargo_temperature_type",
            "cargo_weight_unit": "cargo_weight_unit",
            "container_load_type": "container_load_type",
            "consider_handling_emission": "consider_handling_emission",
            "total_weight_in_tonne": "total_weight_in_tonne",
            "total_distance_km": "total_distance_km",
            "total_co2_kg": "total_co2_kg",
        }

        query_dict = {
            filter_map[key]: value
            for key, value in data.items()
            if value is not None and key in filter_map
        }

        queryset = ShipmentOrder.objects.filter(**query_dict)
        output_serializer = ShipmentReadSerializer(queryset, many=True)
        return Response(
            {"count": queryset.count(), "results": output_serializer.data},
            status=status.HTTP_200_OK,
        )


# views.py
class ShipmentEmissionSummaryAPIView(APIView):
    def get(self, request, shipment_order_id, *args, **kwargs):
        shipment_order = get_object_or_404(
            ShipmentOrder.objects
            .prefetch_related("segments__emission"),
            pk=shipment_order_id
        )
        serializer = ShipmentEmissionSummarySerializer(shipment_order)
        return Response(serializer.data, status=status.HTTP_200_OK)
