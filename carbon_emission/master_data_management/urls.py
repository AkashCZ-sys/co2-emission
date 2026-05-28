from django.urls import path
from master_data_management import views

urlpatterns = [
    path('v1/country_create', views.CountryCreateAPIView.as_view(), name='country_create'),
    path('v1/country_detail/<int:pk>', views.CountryDetailAPIView.as_view(), name='country_detail'),

    path('v1/location_create', views.LocationCreateAPIView.as_view(), name='location_create'),
    path('v1/location_detail/<int:pk>', views.LocationDetailAPIView.as_view(), name='location_detail'),

    path('v1/carrier_create', views.CarrierCreateAPIView.as_view(), name='carrier_create'),
    path('v1/carrier_detail/<int:pk>', views.CarrierDetailAPIView.as_view(), name='carrier_detail'),

    path('v1/company_create', views.CompanyCreateAPIView.as_view(), name='company_create'),
    path('v1/company_detail/<int:pk>', views.CompanyDetailAPIView.as_view(), name='company_detail'),

]


