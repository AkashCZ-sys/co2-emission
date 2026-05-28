from django.db import transaction

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView

from shipment_management.models import (
    ShipmentOrder,
    ShipmentLoadDetail,
    ShipmentSegment,
    ShipmentSegmentEmission
)

from shipment_management.serializers import (
    ShipmentOrderCreateSerializer,
    ShipmentOrderReadSerializer
)


class ShipmentOrderCreateAPIView(CreateAPIView):
    serializer_class = ShipmentOrderCreateSerializer


class ShipmentOrderRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    queryset = ShipmentOrder.objects.prefetch_related("load_details", "segments__emission")
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ShipmentOrderReadSerializer
        return ShipmentOrderCreateSerializer
