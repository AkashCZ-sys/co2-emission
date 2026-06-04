from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from shipment_management.models import ShipmentOrder, ShipmentSegment, ShipmentSegmentEmission, ShipmentLoadDetail
from shipment_management.utility import calculate_distance, EmissionCalculationService, CONTAINER_ADJUSTMENTS


class ShipmentSegmentEmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentSegmentEmission
        fields = (
            "cargo_weight_tonne",
            "distance_km",
            "emission_factor",
            "load_factor",
            "container_adjustment_factor",
            "handling_emission_kg",
            "co2_kg",
            "calculation_metadata",
        )


class ShipmentSegmentSerializer(serializers.ModelSerializer):
    emission = ShipmentSegmentEmissionSerializer(required=False)

    # emission1 = ShipmentSegmentEmissionSerializer(required=False)

    class Meta:
        model = ShipmentSegment
        exclude = ("shipment_order",)


class ShipmentLoadDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentLoadDetail
        exclude = ("shipment_order",)


class ShipmentOrderCreateSerializer(serializers.ModelSerializer):
    load_details = ShipmentLoadDetailSerializer(many=True, required=False)
    segments = ShipmentSegmentSerializer(many=True, required=False)

    class Meta:
        model = ShipmentOrder
        fields = ('shipment_number',
                  'load_details',
                  'segments',
                  'cargo_type',
                  'cargo_temperature_type',
                  'cargo_weight_unit',
                  'container_load_type',)

    @transaction.atomic
    def create(self, validated_data):

        load_details_data = validated_data.pop('load_details', [])
        segments_data = validated_data.pop('segments', [])

        # Create Shipment
        shipment_order = ShipmentOrder.objects.create(**validated_data)

        # Create Load Details
        for load_detail_data in load_details_data:
            ShipmentLoadDetail.objects.create(
                shipment_order=shipment_order,
                **load_detail_data
            )

        # ---------------------------------------------------
        # Shipment-level calculations
        # ---------------------------------------------------

        cargo_weight = 0.0

        for load in shipment_order.load_details.all():
            cargo_weight += (
                    float(load.weight_in_tonne)
                    * float(load.quantity)
            )

        total_qty = 0.0
        weighted_sum = 0.0

        for load in shipment_order.load_details.all():
            factor = float(
                CONTAINER_ADJUSTMENTS.get(
                    load.container_type,
                    1.0
                )
            )

            weighted_sum += (
                    factor * float(load.quantity)
            )

            total_qty += float(load.quantity)

        container_adjustment = (
            weighted_sum / total_qty
            if total_qty else 1.0
        )

        load_factor = 1.0

        total_distance = 0.0
        total_co2 = 0.0

        for segment_data in segments_data:
            segment_data.pop(
                "emission",
                None
            )

            segment = ShipmentSegment.objects.create(
                shipment_order=shipment_order,
                **segment_data
            )

            # Calculate emission
            service = EmissionCalculationService(
                segment=segment,
                cargo_weight=cargo_weight,
                container_adjustment=container_adjustment,
                load_factor=load_factor
            )

            result = service.calculate()

            # Save emission record
            ShipmentSegmentEmission.objects.create(
                shipment_segment=segment,
                cargo_weight_tonne=result[
                    "cargo_weight_t"
                ],
                distance_km=result[
                    "distance_km"
                ],
                emission_factor=result[
                    "emission_factor_g_per_tkm"
                ],
                load_factor=result[
                    "load_factor"
                ],
                container_adjustment_factor=result[
                    "container_adjustment"
                ],
                handling_emission_kg=result[
                    "handling_emission"
                ],
                co2_kg=result[
                    "co2e_kg"
                ],
                calculation_metadata={
                    "formula": "ISO14083_GLEC",
                    "transport_emission": str(
                        result[
                            "transport_emission"
                        ]
                    ),
                    "handling_emission": str(
                        result[
                            "handling_emission"
                        ]
                    ),
                }
            )

            # Update segment distance
            segment.distance_km = result[
                "distance_km"
            ]

            segment.calculated_distance_km = result[
                "distance_km"
            ]

            segment.save(
                update_fields=[
                    "distance_km",
                    "calculated_distance_km"
                ]
            )

            total_distance += float(
                result["distance_km"]
            )

            total_co2 += float(
                result["co2e_kg"]
            )

        # ---------------------------------------------------
        # Update Shipment Totals
        # ---------------------------------------------------

        shipment_order.total_distance_km = total_distance
        shipment_order.total_co2_kg = total_co2

        shipment_order.save(
            update_fields=[
                "total_distance_km",
                "total_co2_kg"
            ]
        )

        return shipment_order


class ShipmentSegmentReadSerializer(serializers.ModelSerializer):
    emission = ShipmentSegmentEmissionSerializer(read_only=True)

    class Meta:
        model = ShipmentSegment
        fields = "__all__"


class ShipmentOrderReadSerializer(serializers.ModelSerializer):
    load_details = ShipmentLoadDetailSerializer(many=True, read_only=True)
    segments = ShipmentSegmentReadSerializer(many=True, read_only=True)

    class Meta:
        model = ShipmentOrder
        fields = "__all__"


class ShipmentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentOrder
        fields = "__all__"


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
