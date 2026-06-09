from django.urls import path

from shipment_management import views
from shipment_management.views import ShipmentEmissionSummaryAPIView

urlpatterns = [
    path("shipment_create", views.ShipmentOrderCreateAPIView.as_view(), name="shipment-order-create"),
    path("shipment_detail/<int:pk>", views.ShipmentOrderRetrieveUpdateDeleteAPIView.as_view(),
         name="shipment-order-detail"),
    path("shipment_list/", views.ShipmentFilterAPIView.as_view(), name="shipment-filter"),
    # urls.py
    path("shipments/<int:shipment_order_id>/emission-summary/", ShipmentEmissionSummaryAPIView.as_view(),
         name="shipment-emission-summary", ),
]
