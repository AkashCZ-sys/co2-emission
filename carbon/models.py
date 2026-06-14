from django.db import models
from tenants.mixins import TenantAwareModel


class Segment(TenantAwareModel):
    """Represents a single leg of a shipment journey."""

    external_segment_ref = models.CharField(max_length=64, blank=True, default="")
    sequence_number = models.PositiveIntegerField()

    transport_mode = models.CharField(max_length=30)
    freight_type = models.CharField(max_length=30, null=True, blank=True)

    origin_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    origin_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    destination_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    destination_longitude = models.DecimalField(max_digits=9, decimal_places=6)

    distance_km = models.FloatField(null=True, blank=True)

    fuel_type = models.CharField(max_length=30, null=True, blank=True)
    fuel_amount = models.FloatField(null=True, blank=True)
    fuel_amount_unit = models.CharField(max_length=10, null=True, blank=True)
    total_payload_tonne = models.FloatField(null=True, blank=True)

    consider_handling_emission = models.BooleanField(default=False)

    class Meta:
        db_table = "SEGMENT"
        ordering = ["sequence_number"]

    def __str__(self):
        return (
            f"Segment #{self.sequence_number} [{self.transport_mode}] "
            f"ref={self.external_segment_ref}"
        )


class SegmentEmission(TenantAwareModel):
    """Stores the computed emission result for one Segment."""

    segment = models.OneToOneField(
        "Segment",
        on_delete=models.CASCADE,
        related_name="emission",
    )

    cargo_weight_tonne = models.FloatField()
    distance_km = models.FloatField()
    activity_tonne_km = models.FloatField()
    allocation_share = models.FloatField()
    co2_kg = models.FloatField()
    calculation_method = models.CharField(max_length=20)

    class Meta:
        db_table = "SEGMENT_EMISSION"
        ordering = ["segment__sequence_number"]

    def __str__(self):
        return (
            f"Emission for Segment #{self.segment_id} "
            f"[{self.calculation_method}] co2={self.co2_kg} kg"
        )

