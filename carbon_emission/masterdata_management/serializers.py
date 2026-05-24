import re

from rest_framework import serializers

from masterdata_management.models import PortOfLoading, PortOfDestination, Country, Carrier, \
    TransportMode, Incoterm, EquipmentType, ShipmentType
from masterdata_management.utility import validate_decimal_coordinate


class PortOfLoadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortOfLoading
        fields = ('id', 'name', 'code', 'country', 'unlocode', 'timezone', 'is_active', "latitude", "longitude",
                  'address', 'description', 'created_on', 'created_by', 'supplyx_code')
        read_only_fields = ['id']

    def validate(self, data):
        """
        validation for create/update operations.
        """
        name = data.get('name')
        code = data.get('code')
        country = data.get('country')
        unlocode = data.get('unlocode')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        address = data.get('address')
        description = data.get('description')

        # Validation for country
        if not country:
            raise serializers.ValidationError({"country": "Country is required."})

        country_obj = Country.objects.filter(id=country).first()
        if not country_obj:
            raise serializers.ValidationError({"country": "Country does not exist."})

        # Validation for name
        # if not name:
        #     raise serializers.ValidationError({"name": "Port name is required."})
        if name:
            if not re.match(r"^[A-Za-z\s\-.,'()]+$", name):
                raise serializers.ValidationError({"name": "Port name must contain only alphabets and punctuation"})
            if len(name) > 50:
                raise serializers.ValidationError({"name": "Port name must be less than 50 characters."})

        # Validation for code
        # if not code:
        #     raise serializers.ValidationError({"code": "Port code is required."})
        # if not re.match(r"^[A-Z0-9]{2,10}$", code):
        #     raise serializers.ValidationError({"code": "Code must be 2–10 uppercase letters or numbers."})

        # Validation for UN/LOCODE
        if not unlocode:
            raise serializers.ValidationError({"code": "unlocode is required."})
        if unlocode:  # Only validate if it's provided
            if not re.match(r"^[A-Z]{2}[A-Z0-9]{3}$", unlocode):
                raise serializers.ValidationError({"unlocode": "UN/LOCODE must be 5 characters (e.g., 'INMAA')."})

        # Validation for latitude and longitude
        validate_decimal_coordinate(latitude, "latitude", -90, 90)
        validate_decimal_coordinate(longitude, "longitude", -180, 180)

        # Validation for address
        if address and len(address) > 255:
            raise serializers.ValidationError({"address": "Address cannot exceed 255 characters."})

        # Validation for description
        if description and len(description) > 500:
            raise serializers.ValidationError({"description": "Description cannot exceed 500 characters."})

        # Validation for unique record
        existing = PortOfLoading.objects.filter(code=code, unlocode=unlocode)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError({"detail": "Port with this code and UN/LOCODE already exists."})

        return data


class PortOfDestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortOfDestination
        fields = ('id', 'name', 'code', 'country', 'unlocode', 'timezone', 'is_active', "latitude", "longitude",
                  'address', 'description', 'created_on', 'created_by', 'supplyx_code')
        read_only_fields = ['id']

    def validate(self, data):
        """
        validation for create/update operations.
        """
        name = data.get('name')
        code = data.get('code')
        country = data.get('country')
        unlocode = data.get('unlocode')
        timezone = data.get('timezone')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        address = data.get('address')
        description = data.get('description')

        # Validation for name
        if name:
            if not re.match(r"^[A-Za-z\s\-.,'()]+$", name):
                raise serializers.ValidationError({"name": "Port name must contain only alphabets and punctuation"})
            if len(name) > 50:
                raise serializers.ValidationError({"name": "Port name must be less than 50 characters."})

        # Validation for code
        # if not code:
        #     raise serializers.ValidationError({"code": "Port code is required."})

        # Validation for UN/LOCODE
        if not unlocode:
            raise serializers.ValidationError({"code": "unlocode is required."})
        if unlocode:
            if not re.match(r"^[A-Z]{2}[A-Z0-9]{3}$", unlocode):
                raise serializers.ValidationError({"unlocode": "UN/LOCODE must be 5 characters (e.g., 'INMAA')."})

        # Validation for country
        # if not country:
        #     raise serializers.ValidationError({"country": "Country is required."})

        # Validation for latitude and longitude
        validate_decimal_coordinate(latitude, "latitude", -90, 90)
        validate_decimal_coordinate(longitude, "longitude", -180, 180)

        # Validation for address
        if address and len(address) > 255:
            raise serializers.ValidationError({"address": "Address cannot exceed 255 characters."})

        # Validation for description
        if description and len(description) > 500:
            raise serializers.ValidationError({"description": "Description cannot exceed 500 characters."})

        # Validation for unique record
        existing = PortOfDestination.objects.filter(code=code, unlocode=unlocode)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError({"detail": "Port with this code and UN/LOCODE already exists."})

        return data


class PortOfLoadingFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    country = serializers.IntegerField(required=False, allow_null=True)
    timezone = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    unlocode = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    address = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(required=False, allow_null=True)
    created_by = serializers.IntegerField(required=False, allow_null=True)
    modified_by = serializers.IntegerField(required=False, allow_null=True)

    order_by = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, write_only=True)
    order_type = serializers.ChoiceField(choices=["asc", "desc"], required=False, allow_blank=True, allow_null=True)
    page = serializers.IntegerField(default=1, allow_null=True)
    page_size = serializers.IntegerField(default=50, allow_null=True)


class PortOfDestinationFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    country = serializers.IntegerField(required=False, allow_null=True)
    unlocode = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    timezone = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    address = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(required=False, allow_null=True)
    created_by = serializers.IntegerField(required=False, allow_null=True)
    modified_by = serializers.IntegerField(required=False, allow_null=True)

    order_by = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, write_only=True)
    order_type = serializers.ChoiceField(choices=["asc", "desc"], required=False, allow_blank=True, allow_null=True)
    page = serializers.IntegerField(default=1, allow_null=True)
    page_size = serializers.IntegerField(default=50, allow_null=True)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = (
            'name', 'code', 'region', 'currency_code', 'currency_name',
        )
        read_only_fields = ['id']

    def validate(self, data):
        name = data.get('name')
        code = data.get('code')
        region = data.get('region')
        currency_code = data.get('currency_code')
        currency_name = data.get('currency_name')

        if not name:
            raise serializers.ValidationError({"name": "Name is required."})
        if name:
            if not re.match(r"^[A-Za-z\s\-.,'()]+$", name):
                raise serializers.ValidationError({"name": "Country name must contain only alphabets and punctuation"})
            if len(name) > 50:
                raise serializers.ValidationError({"name": "Country name must be less than 100 characters."})
        # Validation for unique record
        existing = Country.objects.filter(code=code, currency_code=currency_code, currency_name=currency_name)
        if existing.exists():
            raise serializers.ValidationError(
                {"name": "Country with this code ,currency_code and  currency_name already exists."})
        return data


class CountryReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class CountryFilterSerializer(serializers.Serializer):
    search_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False)
    code = serializers.CharField(max_length=2, required=False, allow_blank=True, allow_null=True, )
    region = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True, )
    currency_code = serializers.CharField(max_length=3, required=False, allow_blank=True, allow_null=True, )
    currency_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, )

    class Meta:
        model = Country
        fields = [
            'id',
            'name',
            'code',
            'region',
            'currency_code',
            'currency_name',

        ]

class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = (
            'name',
            'carrier_code',
            'transportation_mode',
            'description',
        )
        read_only_fields = ['id']

    def validate(self, data):
        name = data.get('name')
        carrier_code = data.get('carrier_code')

        if not name:
            raise serializers.ValidationError(
                {"name": "Carrier name is required."}
            )

        if not re.match(r"^[A-Za-z0-9\s\-.,'()]+$", name):
            raise serializers.ValidationError(
                {"name": "Carrier name contains invalid characters."}
            )

        existing = Carrier.objects.filter(
            name=name,
            carrier_code=carrier_code,
            is_active=True
        )

        if self.instance:
            existing = existing.exclude(id=self.instance.id)

        if existing.exists():
            raise serializers.ValidationError(
                {"name": "Carrier already exists."}
            )

        return data


class CarrierReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = '__all__'


class CarrierFilterSerializer(serializers.Serializer):
    search_value = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )

    name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    carrier_code = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    transportation_mode = serializers.IntegerField(
        required=False,
        allow_null=True
    )


    class Meta:
        model = Carrier
        fields = [
            'id',
            'name',
            'carrier_code',
            'transportation_mode',
        ]

#
# class TransportModeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TransportMode
#         fields = (
#             'mode_name',
#             'description',
#         )
#         read_only_fields = ['id']
#
#     def validate(self, data):
#         mode_name = data.get('mode_name')
#
#         if not mode_name:
#             raise serializers.ValidationError(
#                 {"mode_name": "Mode name is required."}
#             )
#
#         if not re.match(r"^[A-Za-z0-9\s\-.,'()]+$", mode_name):
#             raise serializers.ValidationError(
#                 {"mode_name": "Mode name contains invalid characters."}
#             )
#
#         existing = TransportMode.objects.filter(
#             mode_name__iexact=mode_name
#         )
#
#         if self.instance:
#             existing = existing.exclude(id=self.instance.id)
#
#         if existing.exists():
#             raise serializers.ValidationError(
#                 {"mode_name": "Transport Mode already exists."}
#             )
#
#         return data
#
#
# class TransportModeReadSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TransportMode
#         fields = '__all__'
#
#
# class TransportModeFilterSerializer(serializers.Serializer):
#     search_value = serializers.CharField(
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     mode_name = serializers.CharField(
#         max_length=100,
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     description = serializers.CharField(
#         max_length=250,
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     class Meta:
#         model = TransportMode
#         fields = [
#             'id',
#             'mode_name',
#             'description'
#         ]
#
# class ShipmentTypeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ShipmentType
#         fields = (
#             'mode',
#             'shipment_type_name',
#             'description',
#         )
#         read_only_fields = ['id']
#
#     def validate(self, data):
#         mode = data.get('mode')
#         shipment_type_name = data.get('shipment_type_name')
#
#         if not shipment_type_name:
#             raise serializers.ValidationError(
#                 {"shipment_type_name": "Shipment Type Name is required."}
#             )
#
#         existing = ShipmentType.objects.filter(
#             mode=mode,
#             shipment_type_name__iexact=shipment_type_name
#         )
#
#         if self.instance:
#             existing = existing.exclude(id=self.instance.id)
#
#         if existing.exists():
#             raise serializers.ValidationError(
#                 {"shipment_type_name": "Shipment Type already exists."}
#             )
#
#         return data
#
#
# class ShipmentTypeReadSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ShipmentType
#         fields = '__all__'
#
#
# class ShipmentTypeFilterSerializer(serializers.Serializer):
#     search_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
#
#     mode = serializers.IntegerField(required=False, allow_null=True)
#
#     shipment_type_name = serializers.CharField(
#         max_length=50,
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     class Meta:
#         model = ShipmentType
#         fields = [
#             'id',
#             'mode',
#             'shipment_type_name',
#         ]
#
# class EquipmentTypeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EquipmentType
#         fields = (
#             'mode',
#             'equipment_name',
#             'equipment_category',
#             'description',
#             'iso_code',
#             'supplyx_code',
#             'equipment_size',
#             'equipment_height',
#         )
#         read_only_fields = ['id']
#
#     def validate(self, data):
#         mode = data.get('mode')
#         equipment_name = data.get('equipment_name')
#
#         if not equipment_name:
#             raise serializers.ValidationError(
#                 {"equipment_name": "Equipment Name is required."}
#             )
#
#         existing = EquipmentType.objects.filter(
#             mode=mode,
#             equipment_name__iexact=equipment_name
#         )
#
#         if self.instance:
#             existing = existing.exclude(id=self.instance.id)
#
#         if existing.exists():
#             raise serializers.ValidationError(
#                 {"equipment_name": "Equipment Type already exists."}
#             )
#
#         return data
#
#
# class EquipmentTypeReadSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EquipmentType
#         fields = '__all__'
#
#
# class EquipmentTypeFilterSerializer(serializers.Serializer):
#     search_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
#
#     mode = serializers.IntegerField(required=False, allow_null=True)
#
#     equipment_name = serializers.CharField(
#         max_length=50,
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     equipment_category = serializers.CharField(
#         max_length=50,
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     class Meta:
#         model = EquipmentType
#         fields = [
#             'id',
#             'mode',
#             'equipment_name',
#             'equipment_category',
#         ]
#
# class IncotermSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Incoterm
#         fields = (
#             'incoterm_name',
#             'description',
#         )
#         read_only_fields = ['id']
#
#     def validate(self, data):
#         incoterm_name = data.get('incoterm_name')
#
#         if not incoterm_name:
#             raise serializers.ValidationError(
#                 {"incoterm_name": "Incoterm Name is required."}
#             )
#
#         existing = Incoterm.objects.filter(
#             incoterm_name__iexact=incoterm_name
#         )
#
#         if self.instance:
#             existing = existing.exclude(id=self.instance.id)
#
#         if existing.exists():
#             raise serializers.ValidationError(
#                 {"incoterm_name": "Incoterm already exists."}
#             )
#
#         return data
#
#
# class IncotermReadSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Incoterm
#         fields = '__all__'
#
#
# class IncotermFilterSerializer(serializers.Serializer):
#     search_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
#
#     incoterm_name = serializers.CharField(
#         max_length=50,
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     class Meta:
#         model = Incoterm
#         fields = [
#             'id',
#             'incoterm_name',
#         ]
