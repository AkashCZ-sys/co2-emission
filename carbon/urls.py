from django.urls import path
from . import views

urlpatterns = [
    path('emissions/', views.ShipmentEmissionCalculateView.as_view(), name='shipment_emission_calculate'),
]
