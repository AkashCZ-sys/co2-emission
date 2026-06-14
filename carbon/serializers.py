from rest_framework import serializers


class LoadDetailSerializer(serializers.Serializer):
    container_type = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)
    weight_in_tonne = serializers.FloatField(min_value=0)


class CoordinatesSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class JourneySegmentSerializer(serializers.Serializer):
    external_segment_ref = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    sequence_number = serializers.IntegerField(
        required=False, min_value=1
    )
    transport_mode = serializers.CharField()
    freight_type = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    region = serializers.CharField(
        required=False, allow_blank=True, default="GLOBAL"
    )
    origin_code = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    destination_code = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    origin_coordinates = CoordinatesSerializer(required=True)
    destination_coordinates = CoordinatesSerializer(required=True)

    # Fuel-based fields — all optional; presence triggers FUEL_BASED
    fuel_type = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    fuel_amount = serializers.FloatField(
        required=False, allow_null=True
    )
    fuel_amount_unit = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    total_payload_tonne = serializers.FloatField(
        required=False, allow_null=True
    )

    def validate(self, data):
        # If ANY fuel field is provided, ALL four must be present
        fuel_fields = {
            "fuel_type": data.get("fuel_type"),
            "fuel_amount": data.get("fuel_amount"),
            "fuel_amount_unit": data.get("fuel_amount_unit"),
            "total_payload_tonne": data.get("total_payload_tonne"),
        }
        provided = {k for k, v in fuel_fields.items() if v is not None and v != ""}
        all_four = {"fuel_type", "fuel_amount", "fuel_amount_unit", "total_payload_tonne"}

        if provided and provided != all_four:
            missing = all_four - provided
            raise serializers.ValidationError(
                {
                    "fuel_fields": (
                        f"Partial fuel data supplied. To use FUEL_BASED calculation, "
                        f"all four fields are required. Missing: {', '.join(sorted(missing))}."
                    )
                }
            )

        return data


# class ShipmentEmissionRequestSerializer(serializers.Serializer):
#     calculation_method = serializers.ChoiceField(
#         choices=["DISTANCE_FACTOR", "FUEL_BASED"],
#         default="DISTANCE_FACTOR"
#     )
#
#     cargo_type = serializers.CharField(required=False)
#
#     cargo_temperature_type = serializers.CharField(
#         required=False,
#         allow_blank=True,
#         allow_null=True
#     )
#
#     cargo_weight_unit = serializers.CharField(
#         required=False,
#         default="METRIC_TONNE"
#     )
#
#     container_load_type = serializers.CharField(
#         required=False
#     )
#
#     consider_handling_emission = serializers.BooleanField(
#         default=True
#     )
#
#     load_details = LoadDetailSerializer(
#         many=True,
#         required=False,
#         default=list
#     )
#
#     journey_segments = JourneySegmentSerializer(
#         many=True,
#         required=True
#     )
#
#     def validate(self, data):
#         if not data.get("journey_segments"):
#             raise serializers.ValidationError(
#                 {
#                     "journey_segments":
#                         "At least one journey segment is required."
#                 }
#             )
#
#         if (
#                 data.get("calculation_method") == "FUEL_BASED"
#                 and not any(
#             (
#                     segment.get("fuel_type")
#                     and segment.get("fuel_amount") is not None
#                     and segment.get("fuel_amount_unit")
#                     and segment.get("total_payload_tonne") is not None
#             )
#             for segment in data["journey_segments"]
#         )
#         ):
#             raise serializers.ValidationError(
#                 {
#                     "journey_segments":
#                         "For FUEL_BASED calculation, at least one segment "
#                         "must contain fuel_type, fuel_amount, "
#                         "fuel_amount_unit and total_payload_tonne."
#                 }
#             )
#
#         return data
class ShipmentEmissionRequestSerializer(serializers.Serializer):
    # calculation_method intentionally removed — auto-detected per segment

    cargo_type = serializers.CharField(required=False)
    cargo_temperature_type = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    cargo_weight_unit = serializers.CharField(
        required=False, default="METRIC_TONNE"
    )
    container_load_type = serializers.CharField(required=False)
    consider_handling_emission = serializers.BooleanField(default=True)

    load_details = LoadDetailSerializer(
        many=True, required=False, default=list
    )
    journey_segments = JourneySegmentSerializer(
        many=True, required=True
    )

    def validate(self, data):
        if not data.get("journey_segments"):
            raise serializers.ValidationError(
                {"journey_segments": "At least one journey segment is required."}
            )
        return data
