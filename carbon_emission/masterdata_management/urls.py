from django.urls import path

from masterdata_management import views

urlpatterns = [
    path('v1/pol', views.PortOfLoadingCreateView.as_view(), name='pol_create'),
    path('v1/pol/list', views.PortOfLoadingFilterApi.as_view(), name='pol_list'),
    path('v1/pol/<int:pk>', views.PortOfLoadingUpdateView.as_view(), name='pol_edit'),

    path('v1/pod', views.PortOfDestinationCreateView.as_view(), name='pod_create'),
    path('v1/pod/list', views.PortOfDestinationFilterApi.as_view(), name='pod_list'),
    path('v1/pod/<int:pk>', views.PortOfDestinationUpdateView.as_view(), name='pod_edit'),

    path('v1/country', views.CountryCreateView.as_view(), name='country_create'),
    path('v1/country/<int:pk>', views.CountryUpdateView.as_view(), name='country_edit'),
    path('v1/country/list', views.CountryFilterApiView.as_view(), name='country_list'),

    path('v1/carrier', views.CarrierCreateView.as_view(), name='carrier_create'),
    path('v1/carrier/<int:pk>', views.CarrierUpdateView.as_view(), name='carrier_edit'),
    path('v1/carrier/list', views.CarrierFilterApiView.as_view(), name='carrier_list'),
]
