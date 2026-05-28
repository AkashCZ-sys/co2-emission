from django.urls import path

from shipment_management import views

urlpatterns = [

    path("shipment_create/", views.ShipmentOrderCreateAPIView.as_view(), name="shipment-order-create"),
    path("shipment_detail/<int:pk>/", views.ShipmentOrderRetrieveUpdateDeleteAPIView.as_view(),
         name="shipment-order-detail"),

]
