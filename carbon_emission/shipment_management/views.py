from django.db import transaction
from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView

from shipment_management.models import (
    ShipmentOrder,
    ShipmentLoadDetail,
    ShipmentSegment,
    ShipmentSegmentEmission
)

from shipment_management.serializers import (
    ShipmentOrderCreateSerializer,
    ShipmentOrderReadSerializer, ShipmentReadSerializer, ShipmentFilterSerializer
)


class ShipmentOrderCreateAPIView(CreateAPIView):
    serializer_class = ShipmentOrderCreateSerializer
    queryset = ShipmentOrder.objects.all()


class ShipmentOrderRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ShipmentOrder.objects.prefetch_related("load_details", "segments__emission")
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ShipmentOrderReadSerializer
        return ShipmentOrderCreateSerializer


class ShipmentFilterAPIView(APIView):
    serializer_class = ShipmentReadSerializer

    @extend_schema(request=ShipmentFilterSerializer, responses=ShipmentReadSerializer)
    def post(self, request):
        serializer = ShipmentFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        filter_dict = {
            "shipment_number": "shipment_number",
            "customer": "customer",
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
            filter_dict.get(key): value
            for key, value in data.items()
            if value is not None and filter_dict.get(key)
        }

        queryset = ShipmentOrder.objects.filter(**query_dict)

        output_serializer = ShipmentReadSerializer(
            queryset,
            many=True
        )

        return Response(
            {
                "count": queryset.count(),
                "results": output_serializer.data
            },
            status=status.HTTP_200_OK
        )
