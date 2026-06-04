from django.db import models
from master_data_management.models import Location, Carrier


class ShipmentOrder(models.Model):
    shipment_number = models.CharField(max_length=100, unique=True)
    # customer = models.ForeignKey(Company, on_delete=models.CASCADE)
    cargo_type = models.CharField(max_length=50)
    cargo_temperature_type = models.CharField(max_length=30, blank=True)
    cargo_weight_unit = models.CharField(max_length=20)
    container_load_type = models.CharField(max_length=20)
    consider_handling_emission = models.BooleanField(default=True)
    total_weight_in_tonne = models.DecimalField(max_digits=12, decimal_places=2)
    total_distance_km = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_co2_kg = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        db_table = "SHIPMENT_ORDER"


class ShipmentLoadDetail(models.Model):
    shipment_order = models.ForeignKey(ShipmentOrder, related_name="load_details", on_delete=models.CASCADE)
    container_type = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    weight_in_tonne = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "SHIPMENT_LOAD_DETAIL"


class ShipmentSegment(models.Model):
    shipment_order = models.ForeignKey(ShipmentOrder, related_name="segments", on_delete=models.CASCADE)
    sequence_number = models.PositiveIntegerField()
    transportation_mode = models.PositiveIntegerField()
    carrier = models.ForeignKey(Carrier, on_delete=models.PROTECT, null=True, blank=True)
    freight_type = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=50, blank=True)
    origin_location = models.ForeignKey(Location, related_name="origin_segments", on_delete=models.PROTECT)
    destination_location = models.ForeignKey(Location, related_name="destination_segments", on_delete=models.PROTECT)
    distance_km = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    route_factor = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    calculated_distance_km = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = "SHIPMENT_SEGMENT"
        ordering = ["sequence_number"]


class ShipmentSegmentEmission(models.Model):
    shipment_segment = models.OneToOneField(ShipmentSegment, related_name="emission", on_delete=models.CASCADE)
    cargo_weight_tonne = models.DecimalField(max_digits=12, decimal_places=2)
    distance_km = models.DecimalField(max_digits=15, decimal_places=2)
    emission_factor = models.DecimalField(max_digits=12, decimal_places=6)
    load_factor = models.DecimalField(max_digits=8, decimal_places=4)
    container_adjustment_factor = models.DecimalField(max_digits=8, decimal_places=4)
    handling_emission_kg = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    co2_kg = models.DecimalField(max_digits=18, decimal_places=4)
    calculation_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "SHIPMENT_SEGMENT_EMISSION"
