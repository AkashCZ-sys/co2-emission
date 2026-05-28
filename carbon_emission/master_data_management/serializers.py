from rest_framework import serializers

from master_data_management.models import Carrier, Country, Location, Company


class CountrySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=2)
    region = serializers.CharField(max_length=50)

    class Meta:
        model = Country
        fields = '__all__'

    def validate(self, attrs):
        name = attrs.get('name')
        code = attrs.get('code')

        if Country.objects.filter(name=name, code=code).exists():
            raise serializers.ValidationError('Country already exists')

        return attrs

    def create(self, validated_data):
        return Country.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.code = validated_data.get('code', instance.code)
        instance.region = validated_data.get('region', instance.region)
        instance.save()
        return instance


class CountryReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = '__all__'


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

    def validate(self, attrs):
        code = attrs.get('code')
        unlocode = attrs.get('unlocode')
        iata_code = attrs.get('iata_code')
        lat = attrs.get('lat')
        lon = attrs.get('lon')

        queryset = Location.objects.all()
        # while updating exclude the current id
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if Location.objects.filter(iata_code=iata_code).exists():
            raise serializers.ValidationError('Airport with this ID already exists')
        if Location.objects.filter(unlocode=unlocode).exists():
            raise serializers.ValidationError('Unlocode  for location must be unique')
        if Location.objects.filter(code=code).exists():
            raise serializers.ValidationError('Location already exists')

        return attrs

    def create(self, validated_data):
        return Location.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.code = validated_data.get('code', instance.code)
        instance.iata = validated_data.get('iata', instance.iata)
        instance.lat = validated_data.get('lat', instance.lat)
        instance.lon = validated_data.get('lon', instance.lon)
        instance.unlocode = validated_data.get('unlocode', instance.unlocode)
        instance.country = validated_data.get('country', instance.country)
        instance.city = validated_data.get('city', instance.city)
        instance.state = validated_data.get('state', instance.state)
        instance.address = validated_data.get('address', instance.address)
        instance.save()
        return instance


class CarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = '__all__'

    def validate(self, attrs):
        name = attrs.get('name')
        carrier_code = attrs.get('carrier_code')
        is_active = attrs.get('is_active')

        if Carrier.objects.filter(name=name, carrier_code=carrier_code).exists():
            raise serializers.ValidationError('Carrier already exists')

        if not is_active:
            raise serializers.ValidationError('Carrier not in use')

        return attrs


class CarrierDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    carrier_code = serializers.CharField(max_length=50)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Carrier
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.carrier_code = validated_data.get('carrier_code', instance.carrier_code)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()
        return instance


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

    def validate(self, attrs):
        name = attrs.get('name')
        email = attrs.get('email')

        if Company.objects.filter(name=name).exists():
            raise serializers.ValidationError('Company already exists')
        if Company.objects.filter(email=email).exists():
            raise serializers.ValidationError('Email already exists')

        return attrs


class CompanyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.company_type = validated_data.get('company_type', instance.company_type)
        instance.country = validated_data.get('country', instance.country)
        instance.email = validated_data.get('email', instance.email)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.address = validated_data.get('address', instance.address)

        instance.save()
        return instance
