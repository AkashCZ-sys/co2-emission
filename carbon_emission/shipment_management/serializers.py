from decimal import Decimal

from rest_framework import serializers

from shipment_management.models import ShipmentOrder, ShipmentLoadDetail, ShipmentSegment
from shipment_management.utility import ShipmentEmissionCalculator


# ---------------------------------------------------------------------------
# Shared sub-serializers
# ---------------------------------------------------------------------------

class ShipmentSegmentEmissionSerializer(serializers.Serializer):
    cargo_weight_tonne = serializers.DecimalField(max_digits=12, decimal_places=2)
    distance_km = serializers.DecimalField(max_digits=15, decimal_places=2)
    emission_factor = serializers.DecimalField(max_digits=12, decimal_places=6)
    load_factor = serializers.DecimalField(max_digits=8, decimal_places=4)
    container_adjustment_factor = serializers.DecimalField(max_digits=8, decimal_places=4)
    handling_emission_kg = serializers.DecimalField(max_digits=15, decimal_places=4)
    co2_kg = serializers.DecimalField(max_digits=18, decimal_places=4)
    calculation_metadata = serializers.JSONField(required=False)


class ShipmentLoadDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    container_type = serializers.CharField()
    quantity = serializers.IntegerField()
    weight_in_tonne = serializers.DecimalField(max_digits=12, decimal_places=2)


# ---------------------------------------------------------------------------
# Write (create) serializers
# ---------------------------------------------------------------------------

class ShipmentSegmentWriteSerializer(serializers.Serializer):
    """Used during ShipmentOrder creation — accepts the inbound payload."""
    id = serializers.IntegerField(required=False)
    sequence_number = serializers.IntegerField()
    transportation_mode = serializers.IntegerField()
    # carrier may arrive as int (FK id) or string — store as string
    carrier = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    freight_type = serializers.CharField(required=False, allow_blank=True)
    region = serializers.CharField(required=False, allow_blank=True)
    origin_location = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=True)
    destination_location = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=True)
    origin_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    origin_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    destination_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    destination_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    distance_km = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=Decimal("0"))
    route_factor = serializers.DecimalField(max_digits=8, decimal_places=4, required=False, default=Decimal("1.0"))

    def validate_carrier(self, value):
        """Accept numeric or string carrier — always store as string."""
        if value is None:
            return ""
        return str(value)


class ShipmentOrderCreateSerializer(serializers.Serializer):
    shipment_number = serializers.CharField()
    cargo_type = serializers.CharField()
    cargo_temperature_type = serializers.CharField(required=False, allow_blank=True, default="")
    cargo_weight_unit = serializers.CharField()
    container_load_type = serializers.CharField()
    consider_handling_emission = serializers.BooleanField(required=False, default=True)
    load_details = ShipmentLoadDetailSerializer(many=True, required=False, default=list)
    segments = ShipmentSegmentWriteSerializer(many=True, required=False, default=list)

    def create(self, validated_data):
        load_details_data = validated_data.pop("load_details", [])
        segments_data = validated_data.pop("segments", [])
        # 1. Create the ShipmentOrder
        shipment_order = ShipmentOrder.objects.create(**validated_data)

        # 2. Create load details
        for ld in load_details_data:
            ld.pop("id", None)
            ShipmentLoadDetail.objects.create(shipment_order=shipment_order, **ld)

        # 3. Create segments
        for seg in segments_data:
            seg.pop("id", None)
            ShipmentSegment.objects.create(shipment_order=shipment_order, **seg)

        # 4. Re-fetch with related data so the calculator can access them
        shipment_order.refresh_from_db()

        # 5. Calculate emissions — also persists ShipmentSegmentEmission rows
        emission_result = ShipmentEmissionCalculator(shipment_order).calculate()

        # 6. Save shipment-level totals
        total_distance = sum(seg_result["distance_km"] for seg_result in emission_result["segments"])
        shipment_order.total_weight_in_tonne = Decimal(str(emission_result["cargo_weight"]))
        shipment_order.total_co2_kg = Decimal(str(emission_result["grand_total"]))
        shipment_order.total_distance_km = Decimal(str(round(total_distance, 2)))
        shipment_order.save(update_fields=["total_weight_in_tonne", "total_distance_km", "total_co2_kg"])

        return shipment_order


class ShipmentSegmentReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    shipment_order = serializers.PrimaryKeyRelatedField(read_only=True)
    sequence_number = serializers.IntegerField()
    transportation_mode = serializers.IntegerField()
    carrier = serializers.CharField(required=False, allow_blank=True)
    freight_type = serializers.CharField(required=False, allow_blank=True)
    region = serializers.CharField(required=False, allow_blank=True)
    origin_location = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=True)
    destination_location = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=True)
    origin_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    origin_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    destination_latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    destination_longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    distance_km = serializers.DecimalField(max_digits=15, decimal_places=2)
    route_factor = serializers.DecimalField(max_digits=8, decimal_places=4)
    calculated_distance_km = serializers.DecimalField(max_digits=15, decimal_places=2)
    emission = ShipmentSegmentEmissionSerializer(required=False, read_only=True)


class ShipmentOrderReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    shipment_number = serializers.CharField()
    cargo_type = serializers.CharField()
    cargo_temperature_type = serializers.CharField(required=False, allow_blank=True)
    cargo_weight_unit = serializers.CharField()
    container_load_type = serializers.CharField()
    consider_handling_emission = serializers.BooleanField()
    total_weight_in_tonne = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_distance_km = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_co2_kg = serializers.DecimalField(max_digits=18, decimal_places=4)
    load_details = ShipmentLoadDetailSerializer(many=True, required=False)
    segments = ShipmentSegmentReadSerializer(many=True, required=False)

    def to_representation(self, instance):
        if not hasattr(instance, "_prefetched_objects_cache"):
            instance._segments_qs = (
                ShipmentSegment.objects
                .filter(shipment_order=instance)
                .select_related("emission")
                .order_by("sequence_number")
            )
        return super().to_representation(instance)

    def get_fields(self):
        fields = super().get_fields()
        return fields


class ShipmentReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    shipment_number = serializers.CharField()
    cargo_type = serializers.CharField()
    cargo_temperature_type = serializers.CharField(required=False, allow_blank=True)
    cargo_weight_unit = serializers.CharField()
    container_load_type = serializers.CharField()
    consider_handling_emission = serializers.BooleanField()
    total_weight_in_tonne = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_distance_km = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_co2_kg = serializers.DecimalField(max_digits=18, decimal_places=4)


class ShipmentFilterSerializer(serializers.Serializer):
    shipment_number = serializers.CharField(required=False)
    cargo_type = serializers.CharField(required=False)
    cargo_temperature_type = serializers.CharField(required=False)
    cargo_weight_unit = serializers.CharField(required=False)
    container_load_type = serializers.CharField(required=False)
    consider_handling_emission = serializers.BooleanField(required=False)
    total_weight_in_tonne = serializers.FloatField(required=False)
    total_distance_km = serializers.FloatField(required=False)
    total_co2_kg = serializers.FloatField(required=False)


# serializers.py

class SegmentEmissionBreakdownSerializer(serializers.Serializer):
    """Per-segment slice — mirrors ShipmentSegmentReadSerializer.emission"""
    sequence_number = serializers.IntegerField()
    origin_location = serializers.CharField()
    destination_location = serializers.CharField()
    transportation_mode = serializers.IntegerField()
    freight_type = serializers.CharField()
    distance_km = serializers.DecimalField(max_digits=15, decimal_places=2)
    calculated_distance_km = serializers.DecimalField(max_digits=15, decimal_places=2)
    # from the related ShipmentSegmentEmission row
    cargo_weight_tonne = serializers.DecimalField(
        source="emission.cargo_weight_tonne",
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    emission_factor = serializers.DecimalField(
        source="emission.emission_factor",
        max_digits=12,
        decimal_places=6,
        read_only=True
    )

    load_factor = serializers.DecimalField(
        source="emission.load_factor",
        max_digits=8,
        decimal_places=4,
        read_only=True
    )

    container_adjustment_factor = serializers.DecimalField(
        source="emission.container_adjustment_factor",
        max_digits=8,
        decimal_places=4,
        read_only=True
    )

    handling_emission_kg = serializers.DecimalField(
        source="emission.handling_emission_kg",
        max_digits=15,
        decimal_places=4,
        read_only=True
    )

    co2_kg = serializers.DecimalField(
        source="emission.co2_kg",
        max_digits=18,
        decimal_places=4,
        read_only=True
    )

    def get_transport_emission_kg(self, obj):
        transport_emission_kg = serializers.SerializerMethodField()
        metadata = getattr(obj.emission, "calculation_metadata", {}) or {}
        return metadata.get(transport_emission_kg, 0.0)


class ShipmentEmissionSummarySerializer(serializers.Serializer):
    """
    Combines ShipmentOrderReadSerializer (overall totals)
    + ShipmentSegmentReadSerializer (per-segment breakdown)
    into one response shape.
    """
    id = serializers.IntegerField()
    shipment_number = serializers.CharField()
    cargo_type = serializers.CharField()
    container_load_type = serializers.CharField()

    # --- overall (from ShipmentOrder fields) ---
    overall = serializers.SerializerMethodField()

    # --- per-segment breakdown ---
    segments = serializers.SerializerMethodField()

    def get_overall(self, obj):
        return {
            "total_weight_tonne": obj.total_weight_in_tonne,
            "total_distance_km": obj.total_distance_km,
            "total_co2_kg": obj.total_co2_kg,
            "segment_count": obj.segments.count(),
        }

    def get_segments(self, obj):
        segments = obj.segments.all().order_by("sequence_number")
        return SegmentEmissionBreakdownSerializer(segments, many=True).data
