from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from master_data_management.models import Carrier, Country, Location
from master_data_management.serializers import CountrySerializer, LocationSerializer, CarrierSerializer, \
    CarrierDetailSerializer, CountryReadSerializer, LocationReadSerializer, \
    CarrierReadSerializer, CountryFilterSerializer, LocationFilterSerializer, \
    CarrierFilterSerializer


class CountryCreateAPIView(CreateAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    def perform_create(self, serializer):
        serializer.save()


class CountryListAPIView(APIView):
    serializer_class = CountryReadSerializer

    @extend_schema(
        request=CountryFilterSerializer,
        responses=CountryReadSerializer
    )
    def post(self, request):
        serializer = CountryFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            # Pagination
            page_size = data.get("page_size") or 50
            page = data.get("page") or 1

            if page < 1 or page_size < 1:
                return Response(
                    {"message": "page and page_size should be positive integers"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Filter mapping
            filter_dict = {
                "name": "name__icontains",
                "code": "code__iexact",
                "region": "region__icontains",

            }

            # Dynamic filters
            query_dict = {
                filter_dict[key]: value
                for key, value in data.items()
                if value is not None and key in filter_dict
            }

            # Base queryset
            base_queryset = Country.objects.filter(**query_dict)

            # Global search
            search = data.get("search")
            if search:
                search_q = (
                        Q(name__icontains=search)
                        | Q(code__icontains=search)
                        | Q(region__icontains=search)
                )
                base_queryset = base_queryset.filter(search_q)

            # Ordering
            order_by_dict = {
                "name": "name",
                "code": "code",
                "region": "region",

            }

            order_by_field = order_by_dict.get(data.get("order_by"))

            if order_by_field:
                if data.get("order_type") == "desc":
                    order_by_field = f"-{order_by_field}"

                base_queryset = base_queryset.order_by(order_by_field)

            # Pagination
            paginator = Paginator(base_queryset, page_size)

            if page > paginator.num_pages and paginator.num_pages > 0:
                return Response(
                    {"message": "Page not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            page_obj = paginator.get_page(page)

            output_serializer = self.serializer_class(
                page_obj,
                many=True,
                context={"request": request}
            )

            return Response(
                {
                    "count": base_queryset.count(),
                    "results": output_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CountryDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class LocationCreateAPIView(CreateAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer

    def perform_create(self, serializer):
        serializer.save()


class LocationDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class LocationListAPIView(ListAPIView):
    serializer_class = LocationReadSerializer

    @extend_schema(request=LocationFilterSerializer, responses=LocationReadSerializer)
    def post(self, request):
        serializer = LocationFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            # Pagination
            page_size = data.get("page_size") or 50
            page = data.get("page") or 1

            if page < 1 or page_size < 1:
                return Response(
                    {"message": "page and page_size should be positive integers"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Filter mapping
            filter_dict = {
                "name": "name__icontains",
                "code": "code__iexact",
                "unlocode": "unlocode__icontains",
                "iata_code": "iata_code__icontains",
                "country": "country__icontains",
                "city": "city__icontains",
                "state": "state__icontains",
                "address": "address__icontains",
                "latitude": "latitude__iexact",
                "longitude": "longitude__iexact",
                "location_type": "location_type__icontains",

            }

            # Dynamic filters
            query_dict = {
                filter_dict[key]: value
                for key, value in data.items()
                if value is not None and key in filter_dict
            }

            # Base queryset
            base_queryset = Country.objects.filter(**query_dict)

            # Global search
            search = data.get("search")
            if search:
                search_q = (
                        Q(name__icontains=search)
                        | Q(code__icontains=search)
                        | Q(unlocode__icontains=search)
                        | Q(city__icontains=search)
                        | Q(state__icontains=search)
                        | Q(address__icontains=search)
                        | Q(iata_code__icontains=search)
                        | Q(country__icontains=search)
                        | Q(latitude__icontains=search)
                        | Q(longitude__icontains=search)
                )
                base_queryset = base_queryset.filter(search_q)

            # Ordering
            order_by_dict = {
                "name": "name__icontains",
                "code": "code__iexact",
                "unlocode": "unlocode__icontains",
                "iata_code": "iata_code__icontains",
                "country": "country__icontains",
                "city": "city__icontains",
                "state": "state__icontains",
                "address": "address__icontains",
                "latitude": "latitude__iexact",
                "longitude": "longitude__iexact",
                "location_type": "location_type__icontains",

            }

            order_by_field = order_by_dict.get(data.get("order_by"))

            if order_by_field:
                if data.get("order_type") == "desc":
                    order_by_field = f"-{order_by_field}"

                base_queryset = base_queryset.order_by(order_by_field)

            # Pagination
            paginator = Paginator(base_queryset, page_size)

            if page > paginator.num_pages and paginator.num_pages > 0:
                return Response(
                    {"message": "Page not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            page_obj = paginator.get_page(page)

            output_serializer = self.serializer_class(
                page_obj,
                many=True,
                context={"request": request}
            )

            return Response(
                {
                    "count": base_queryset.count(),
                    "results": output_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CarrierCreateAPIView(CreateAPIView):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer


class CarrierDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Carrier.objects.all()
    serializer_class = CarrierDetailSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CarrierListAPIView(APIView):
    serializer_class = CountryReadSerializer

    @extend_schema(
        request=CarrierFilterSerializer,
        responses=CarrierReadSerializer
    )
    def post(self, request):
        serializer = CarrierFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            # Pagination
            page_size = data.get("page_size") or 50
            page = data.get("page") or 1

            if page < 1 or page_size < 1:
                return Response(
                    {"message": "page and page_size should be positive integers"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Filter mapping
            filter_dict = {
                "name": "name__icontains",
                "carrier_code": "carrier_code__iexact",
                "transportation_mode": "transportation_mode__icontains",
                "is_active": "is_active__iexact",

            }

            # Dynamic filters
            query_dict = {
                filter_dict[key]: value
                for key, value in data.items()
                if value is not None and key in filter_dict
            }

            # Base queryset
            base_queryset = Country.objects.filter(**query_dict)

            # Global search
            search = data.get("search")
            if search:
                search_q = (
                        Q(name__icontains=search)
                        | Q(carrier_code__icontains=search)
                        | Q(transportation_mode__icontains=search)
                        | Q(is_active__iexact=search)
                )
                base_queryset = base_queryset.filter(search_q)

            # Ordering
            order_by_dict = {
                "name": "name__icontains",
                "carrier_code": "carrier_code__iexact",
                "transportation_mode": "transportation_mode__icontains",
                "is_active": "is_active__iexact",

            }

            order_by_field = order_by_dict.get(data.get("order_by"))

            if order_by_field:
                if data.get("order_type") == "desc":
                    order_by_field = f"-{order_by_field}"

                base_queryset = base_queryset.order_by(order_by_field)

            # Pagination
            paginator = Paginator(base_queryset, page_size)

            if page > paginator.num_pages and paginator.num_pages > 0:
                return Response(
                    {"message": "Page not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            page_obj = paginator.get_page(page)

            output_serializer = self.serializer_class(
                page_obj,
                many=True,
                context={"request": request}
            )

            return Response(
                {
                    "count": base_queryset.count(),
                    "results": output_serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
