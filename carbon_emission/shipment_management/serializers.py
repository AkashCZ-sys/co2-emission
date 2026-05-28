from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from shipment_management.models import ShipmentOrder, ShipmentSegment, ShipmentSegmentEmission, ShipmentLoadDetail
from shipment_management.utility import calculate_distance,  EmissionCalculationService


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
        fields = (
            'shipment_number',
            'load_details',
            'segments',
            'customer',
            'cargo_type',
            'cargo_temperature_type',
            'cargo_weight_unit',
            'container_load_type',
            'consider_handling_emission',
            'total_weight_in_tonne',
            'total_distance_km',
            'total_co2_kg'
        )

    @transaction.atomic
    def create(self, validated_data):

        load_details_data = validated_data.pop(
            'load_details',
            []
        )

        segments_data = validated_data.pop(
            'segments',
            []
        )

        # Create Shipment
        shipment_order = ShipmentOrder.objects.create(
            **validated_data
        )

        # Create Load Details
        for load_detail_data in load_details_data:
            ShipmentLoadDetail.objects.create(
                shipment_order=shipment_order,
                **load_detail_data
            )

        # Initialize Service
        service = EmissionCalculationService(
            shipment_order
        )

        total_distance = Decimal("0")
        total_co2 = Decimal("0")

        # Create Segments
        for segment_data in segments_data:
            emission_data = segment_data.pop(
                'emission',
                None
            )

            segment = ShipmentSegment.objects.create(
                shipment_order=shipment_order,
                **segment_data
            )

            # Calculate Distance
            distance = Decimal(
                str(
                    calculate_distance(segment)
                )
            )

            # Calculate Emission
            result = (
                service.calculate_segment_emission(
                    segment,
                    distance
                )
            )

            # Save emission record
            ShipmentSegmentEmission.objects.create(
                shipment_segment=segment,

                cargo_weight_tonne=result[
                    "cargo_weight"
                ],

                distance_km=result[
                    "distance"
                ],

                emission_factor=result[
                    "factor"
                ],

                load_factor=Decimal("1"),

                container_adjustment_factor=result[
                    "adjustment"
                ],

                handling_emission_kg=result[
                    "handling_emission"
                ],

                co2_kg=result[
                    "total"
                ],

                calculation_metadata={
                    "formula":
                        "ISO14083_GLEC",
                    "transport_emission":
                        str(
                            result[
                                "transport_emission"
                            ]
                        ),
                    "handling_emission":
                        str(
                            result[
                                "handling_emission"
                            ]
                        ),
                }
            )

            # Update segment distance
            segment.distance_km = distance

            segment.calculated_distance_km = (
                distance
            )

            segment.save(
                update_fields=[
                    "distance_km",
                    "calculated_distance_km"
                ]
            )

            total_distance += distance

            total_co2 += result["total"]

        # Update Shipment Totals
        shipment_order.total_distance_km = (
            total_distance
        )

        shipment_order.total_co2_kg = (
            total_co2
        )

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
