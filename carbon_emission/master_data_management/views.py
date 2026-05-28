from django.shortcuts import render
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView

from master_data_management.models import Carrier, Country, Location, Company
from master_data_management.serializers import CountrySerializer, LocationSerializer, CarrierSerializer, \
    CarrierDetailSerializer, CompanySerializer, CompanyDetailSerializer


class CountryCreateAPIView(CreateAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    def perform_create(self, serializer):
        serializer.save()


class CountryDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


# Country Filter baad mein karenge

class LocationCreateAPIView(CreateAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def perform_create(self, serializer):
        serializer.save()


class LocationDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class CarrierCreateAPIView(CreateAPIView):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class CarrierDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Carrier.objects.all()
    serializer_class = CarrierDetailSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CompanyCreateAPIView(CreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class CompanyDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanyDetailSerializer
