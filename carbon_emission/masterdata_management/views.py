from django.core.paginator import Paginator
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, serializers
from rest_framework.generics import CreateAPIView, GenericAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from carbon_emission.utility import apply_date_time_range_filters
from masterdata_management.models import PortOfLoading, PortOfDestination, Country, Incoterm, \
    EquipmentType, ShipmentType, TransportMode, Carrier
from masterdata_management.serializers import PortOfLoadingSerializer, PortOfLoadingFilterSerializer, \
    PortOfDestinationSerializer, PortOfDestinationFilterSerializer, CountrySerializer, CountryFilterSerializer, \
    CountryReadSerializer,CarrierReadSerializer, CarrierFilterSerializer, CarrierSerializer
from masterdata_management.utility import build_port_global_search_q
from shipment_management.models import ShipmentOrder


class PortOfLoadingCreateView(CreateAPIView):
    """
    This view class is used to create a new Port of Loading entry.
    """
    serializer_class = PortOfLoadingSerializer
    queryset = PortOfLoading.objects.all()


class PortOfLoadingFilterApi(GenericAPIView):
    """
    This view class is used to return Port of Loading entries with filtering and pagination using POST request.
    """
    serializer_class = PortOfLoadingFilterSerializer

    @extend_schema(request=PortOfLoadingFilterSerializer)
    def post(self, request):
        serializer = PortOfLoadingFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            page_size = data.get("page_size", 50) if data.get("page_size") is not None else 50
            page = data.get("page", 1) if data.get("page") is not None else 1
            if page < 1 or page_size < 1:
                return Response({"message": "page and page_size should be positive integer"},
                                status=status.HTTP_400_BAD_REQUEST)
            order_by = request.data.get('order_by', None)
            order_type = request.data.get('order_type')

            # Filter mapping
            filter_dict = {
                "name": "name__icontains",
                "code": "code__icontains",
                "country": "country__icontains",
                "created_by": "created_by",
                "modified_by": "modified_by",
                "timezone": "timezone__icontains",
                "latitude": "latitude",
                "longitude": "longitude",
                "unlocode": "unlocode",
                "address": "address",
                "description": "description",
                "is_active": "is_active"
            }

            query_dict = {filter_dict.get(key, None): value for key, value in data.items() if
                          value or isinstance(value, (int, float))}
            query_dict = {key: value for key, value in query_dict.items() if key}

            queryset = PortOfLoading.objects.filter(**query_dict).order_by("name")

            queryset = apply_date_time_range_filters(queryset, data)

            search_value = data.get("search")
            global_q = build_port_global_search_q(search_value) if search_value else None

            if global_q:
                queryset = queryset.filter(global_q)

            total_count = PortOfLoading.objects.aggregate(
                total_active=Count('id', filter=Q(is_active=True)),
                total_inactive=Count('id', filter=Q(is_active=False))
            )
            total_is_active = total_count['total_active'] or 0
            total_inactive = total_count['total_inactive'] or 0

            # Order mapping
            order_by_dict = {
                "name": "name",
                "code": "code",
                "country": "country",
                "created_on": "created_on",
                "modified_on": "modified_on",
                "created_by": "created_by",
                "modified_by": "modified_by",
                "is_active": "is_active",
                "latitude": "latitude",
                "longitude": "longitude",
                "unlocode": "unlocode",
                "address": "address",
                "description": "description"
            }

            query_filter = order_by_dict.get(order_by, None)
            if order_type == "desc" and query_filter:
                query_filter = f"-{query_filter}"
            if query_filter:
                queryset = queryset.order_by(query_filter)

            # Create Paginator object with page_size objects per page
            paginator = Paginator(queryset, page_size)
            number_pages = paginator.num_pages
            if page > number_pages and page > 1:
                return Response({"message": "Page not found"}, status=status.HTTP_400_BAD_REQUEST)
            # Get the page object for the requested page number
            page_obj = paginator.get_page(page)
            serializer = PortOfLoadingSerializer(page_obj, many=True, context=self.request)
            data = serializer.data
            return Response(
                {"count": queryset.count(), "total_is_active": total_is_active, "total_inactive": total_inactive,
                 "results": data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PortOfLoadingUpdateView(RetrieveUpdateDestroyAPIView):
    """
    This view class is used to update an existing Port of Loading entry.
    The ID should be passed in the URL path.
    """

    serializer_class = PortOfLoadingSerializer
    queryset = PortOfLoading.objects.all()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        if ShipmentOrder.objects.filter(pol_id=instance.id, is_active=True).exists():
            raise serializers.ValidationError({"detail": "Cannot delete. This record is referenced by ShipmentOrder."})
        instance.is_active = False
        instance.save()


class PortOfDestinationCreateView(CreateAPIView):
    """
    This view class is used to create a new port of Destination entry.
    """
    serializer_class = PortOfDestinationSerializer
    queryset = PortOfDestination.objects.all()

    def perform_create(self, serializer):
        serializer.save()


class PortOfDestinationFilterApi(GenericAPIView):
    """
    This view class is used to return Port of Destination entries with filtering and pagination using POST request.
    """
    serializer_class = PortOfDestinationFilterSerializer

    @extend_schema(request=PortOfDestinationFilterSerializer)
    def post(self, request):
        serializer = PortOfDestinationFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            page_size = data.get("page_size", 50) if data.get("page_size") is not None else 50
            page = data.get("page", 1) if data.get("page") is not None else 1
            if page < 1 or page_size < 1:
                return Response({"message": "page and page_size should be positive integer"},
                                status=status.HTTP_400_BAD_REQUEST)
            order_by = request.data.get('order_by', None)
            order_type = request.data.get('order_type')

            # Filter mapping
            filter_dict = {
                "name": "name__icontains",
                "code": "code__icontains",
                "country": "country__icontains",
                "timezone": "timezone__icontains",
                "latitude": "latitude",
                "longitude": "longitude",
                "created_by": "created_by",
                "modified_by": "modified_by",
                "unlocode": "unlocode",
                "address": "address",
                "description": "description",
                "is_active": "is_active"
            }
            query_dict = {filter_dict.get(key, None): value for key, value in data.items() if
                          value or isinstance(value, (int, float))}
            query_dict = {key: value for key, value in query_dict.items() if key}
            # query_dict["is_active"] = True

            queryset = PortOfDestination.objects.filter(**query_dict).order_by("name")
            queryset = apply_date_time_range_filters(queryset, data)

            # Dynamic search
            search_value = data.get("search")
            global_q = build_port_global_search_q(search_value) if search_value else None

            if global_q:
                queryset = queryset.filter(global_q)

            total_count = PortOfDestination.objects.aggregate(
                total_active=Count('id', filter=Q(is_active=True)),
                total_inactive=Count('id', filter=Q(is_active=False))
            )
            total_is_active = total_count['total_active'] or 0
            total_inactive = total_count['total_inactive'] or 0

            # Order mapping
            order_by_dict = {
                "name": "name",
                "code": "code",
                "country": "country",
                "created_on": "created_on",
                "modified_on": "modified_on",
                "created_by": "created_by",
                "modified_by": "modified_by",
                "is_active": "is_active",
                "latitude": "latitude",
                "longitude": "longitude",
                "unlocode": "unlocode",
                "address": "address",
                "description": "description"
            }
            query_filter = order_by_dict.get(order_by, None)
            if order_type == "desc" and query_filter:
                query_filter = f"-{query_filter}"
            if query_filter:
                queryset = queryset.order_by(query_filter)

            # Create Paginator object with page_size objects per page
            paginator = Paginator(queryset, page_size)
            number_pages = paginator.num_pages
            if page > number_pages and page > 1:
                return Response({"message": "Page not found"}, status=status.HTTP_400_BAD_REQUEST)
            # Get the page object for the requested page number
            page_obj = paginator.get_page(page)
            serializer = PortOfDestinationSerializer(page_obj, many=True, context=self.request)
            data = serializer.data
            return Response(
                {"count": queryset.count(), "total_is_active": total_is_active, "total_inactive": total_inactive,
                 "results": data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PortOfDestinationUpdateView(RetrieveUpdateDestroyAPIView):
    """
    This view class is used to update an existing Port of Loading entry.
    The ID should be passed in the URL path.
    """
    serializer_class = PortOfDestinationSerializer
    queryset = PortOfDestination.objects.all()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        if ShipmentOrder.objects.filter(pod_id=instance.id, is_active=True).exists():
            raise serializers.ValidationError({"detail": "Cannot delete. This record is referenced by ShipmentOrder."})
        instance.is_active = False
        instance.save()


class CountryCreateView(CreateAPIView):
    serializer_class = CountrySerializer
    queryset = Country.objects.all()


class CountryUpdateView(RetrieveUpdateDestroyAPIView):
    serializer_class = CountrySerializer
    queryset = Country.objects.all()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        if ShipmentOrder.objects.filter(pol_id=instance.id, is_active=True).exists():
            raise serializers.ValidationError({"detail": "Cannot delete. This record is referenced by ShipmentOrder."})
        instance.is_active = False
        instance.save()


class CountryFilterApiView(GenericAPIView):
    serializer_class = CountryFilterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            page_size = data.get("page_size", 50) or 50
            page = data.get("page", 1) or 1

            if page < 1 or page_size < 1:
                return Response(
                    {"message": "page and page_size should be positive integer"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            filter_dict = {
                'name': 'name',
                'code': 'code',
                'region': 'region',
                'currency_code': 'currency_code',
                'currency_name': 'currency_name',

            }

            query_dict = {
                filter_dict[key]: value
                for key, value in data.items()
                if key in filter_dict and value not in [None, ""]
            }

            queryset = Country.objects.filter(**query_dict).order_by("name")

            search_value = data.get("search_value")
            if search_value:
                queryset = queryset.filter(
                    Q(name__icontains=search_value) |
                    Q(code__icontains=search_value) |
                    Q(region__icontains=search_value) |
                    Q(currency_code__icontains=search_value) |
                    Q(currency_name__icontains=search_value)

                )

            total_count = queryset.count()

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            serializer = CountryReadSerializer(page_obj, many=True)

            return Response({
                "count": total_count,
                "results": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CarrierCreateView(CreateAPIView):
    serializer_class = CarrierSerializer
    queryset = Carrier.objects.all()


class CarrierUpdateView(RetrieveUpdateDestroyAPIView):
    serializer_class = CarrierSerializer
    queryset = Carrier.objects.all()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CarrierFilterApiView(GenericAPIView):
    serializer_class = CarrierFilterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            page_size = data.get("page_size", 50) or 50
            page = data.get("page", 1) or 1

            if page < 1 or page_size < 1:
                return Response(
                    {
                        "message":
                            "page and page_size should be positive integer"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            filter_dict = {
                "name": "name",
                "carrier_code": "carrier_code",
                "transportation_mode": "transportation_mode",
                "supplyx_code": "supplyx_code",
            }

            query_dict = {
                filter_dict[key]: value
                for key, value in data.items()
                if key in filter_dict and value not in [None, ""]
            }

            queryset = Carrier.objects.filter(
                is_active=True,
                **query_dict
            ).order_by("name")

            search_value = data.get("search_value")

            if search_value:
                queryset = queryset.filter(
                    Q(name__icontains=search_value) |
                    Q(carrier_code__icontains=search_value) |
                    Q(supplyx_code__icontains=search_value)
                )

            total_count = queryset.count()

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            serializer = CarrierReadSerializer(
                page_obj,
                many=True
            )

            return Response(
                {
                    "count": total_count,
                    "results": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

#
# class TransportModeCreateView(CreateAPIView):
#     serializer_class = TransportModeSerializer
#     queryset = TransportMode.objects.all()
#
#
# class TransportModeUpdateView(RetrieveUpdateDestroyAPIView):
#     serializer_class = TransportModeSerializer
#     queryset = TransportMode.objects.all()
#
#     def perform_update(self, serializer):
#         serializer.save()
#
#     def perform_destroy(self, instance):
#         instance.is_active = False
#         instance.save()
#
#
# class TransportModeFilterApiView(GenericAPIView):
#     serializer_class = TransportModeFilterSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         data = serializer.validated_data
#
#         try:
#             page_size = data.get("page_size", 50) or 50
#             page = data.get("page", 1) or 1
#
#             if page < 1 or page_size < 1:
#                 return Response(
#                     {"message": "page and page_size should be positive integer"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#
#             filter_dict = {
#                 'mode_name': 'mode_name',
#                 'description': 'description',
#             }
#
#             query_dict = {
#                 filter_dict[key]: value
#                 for key, value in data.items()
#                 if key in filter_dict and value not in [None, ""]
#             }
#
#             queryset = TransportMode.objects.filter(
#                 is_active=True,
#                 **query_dict
#             ).order_by("mode_name")
#
#             search_value = data.get("search_value")
#
#             if search_value:
#                 queryset = queryset.filter(
#                     Q(mode_name__icontains=search_value) |
#                     Q(description__icontains=search_value)
#                 )
#
#             total_count = queryset.count()
#
#             paginator = Paginator(queryset, page_size)
#             page_obj = paginator.get_page(page)
#
#             serializer = TransportModeReadSerializer(
#                 page_obj,
#                 many=True
#             )
#
#             return Response(
#                 {
#                     "count": total_count,
#                     "results": serializer.data
#                 },
#                 status=status.HTTP_200_OK
#             )
#
#         except Exception as e:
#             return Response(
#                 {"detail": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#
# class ShipmentTypeCreateView(CreateAPIView):
#     serializer_class = ShipmentTypeSerializer
#     queryset = ShipmentType.objects.all()
#
#
# class ShipmentTypeUpdateView(RetrieveUpdateDestroyAPIView):
#     serializer_class = ShipmentTypeSerializer
#     queryset = ShipmentType.objects.all()
#
#     def perform_update(self, serializer):
#         serializer.save()
#
#     def perform_destroy(self, instance):
#         instance.is_active = False
#         instance.save()
#
#
# class ShipmentTypeFilterApiView(GenericAPIView):
#     serializer_class = ShipmentTypeFilterSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         data = serializer.validated_data
#
#         try:
#             page_size = data.get("page_size", 50) or 50
#             page = data.get("page", 1) or 1
#
#             filter_dict = {
#                 'mode': 'mode',
#                 'shipment_type_name': 'shipment_type_name',
#             }
#
#             query_dict = {
#                 filter_dict[key]: value
#                 for key, value in data.items()
#                 if key in filter_dict and value not in [None, ""]
#             }
#
#             queryset = ShipmentType.objects.filter(
#                 is_active=True,
#                 **query_dict
#             ).order_by("shipment_type_name")
#
#             search_value = data.get("search_value")
#
#             if search_value:
#                 queryset = queryset.filter(
#                     Q(shipment_type_name__icontains=search_value)
#                 )
#
#             total_count = queryset.count()
#
#             paginator = Paginator(queryset, page_size)
#             page_obj = paginator.get_page(page)
#
#             serializer = ShipmentTypeReadSerializer(page_obj, many=True)
#
#             return Response(
#                 {
#                     "count": total_count,
#                     "results": serializer.data
#                 },
#                 status=status.HTTP_200_OK
#             )
#
#         except Exception as e:
#             return Response(
#                 {"detail": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#
# class EquipmentTypeCreateView(CreateAPIView):
#     serializer_class = EquipmentTypeSerializer
#     queryset = EquipmentType.objects.all()
#
#
# class EquipmentTypeUpdateView(RetrieveUpdateDestroyAPIView):
#     serializer_class = EquipmentTypeSerializer
#     queryset = EquipmentType.objects.all()
#
#     def perform_update(self, serializer):
#         serializer.save()
#
#     def perform_destroy(self, instance):
#         instance.is_active = False
#         instance.save()
#
#
# class EquipmentTypeFilterApiView(GenericAPIView):
#     serializer_class = EquipmentTypeFilterSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         data = serializer.validated_data
#
#         try:
#             page_size = data.get("page_size", 50) or 50
#             page = data.get("page", 1) or 1
#
#             filter_dict = {
#                 'mode': 'mode',
#                 'equipment_name': 'equipment_name',
#                 'equipment_category': 'equipment_category',
#             }
#
#             query_dict = {
#                 filter_dict[key]: value
#                 for key, value in data.items()
#                 if key in filter_dict and value not in [None, ""]
#             }
#
#             queryset = EquipmentType.objects.filter(
#                 is_active=True,
#                 **query_dict
#             ).order_by("equipment_name")
#
#             search_value = data.get("search_value")
#
#             if search_value:
#                 queryset = queryset.filter(
#                     Q(equipment_name__icontains=search_value) |
#                     Q(equipment_category__icontains=search_value) |
#                     Q(iso_code__icontains=search_value) |
#                     Q(supplyx_code__icontains=search_value)
#                 )
#
#             total_count = queryset.count()
#
#             paginator = Paginator(queryset, page_size)
#             page_obj = paginator.get_page(page)
#
#             serializer = EquipmentTypeReadSerializer(page_obj, many=True)
#
#             return Response(
#                 {
#                     "count": total_count,
#                     "results": serializer.data
#                 },
#                 status=status.HTTP_200_OK
#             )
#
#         except Exception as e:
#             return Response(
#                 {"detail": str(e)},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#
# class IncotermCreateView(CreateAPIView):
#     serializer_class = IncotermSerializer
#     queryset = Incoterm.objects.all()
#
#
# class IncotermUpdateView(RetrieveUpdateDestroyAPIView):
#     serializer_class = IncotermSerializer
#     queryset = Incoterm.objects.all()
#
#     def perform_update(self, serializer):
#         serializer.save()
#
#     def perform_destroy(self, instance):
#         instance.is_active = False
#         instance.save()
#
#
# class IncotermFilterApiView(GenericAPIView):
#     serializer_class = IncotermFilterSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         data = serializer.validated_data
#
#         queryset = Incoterm.objects.filter(is_active=True)
#
#         if data.get("incoterm_name"):
#             queryset = queryset.filter(
#                 incoterm_name=data["incoterm_name"]
#             )
#
#         if data.get("search_value"):
#             queryset = queryset.filter(
#                 Q(incoterm_name__icontains=data["search_value"])
#             )
#
#         serializer = IncotermReadSerializer(queryset, many=True)
#
#         return Response(
#             {
#                 "count": queryset.count(),
#                 "results": serializer.data
#             }
#         )
