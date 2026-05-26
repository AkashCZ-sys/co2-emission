from django.db import models

from carbon_emission.utility import BaseUserModel
from shipment_management.utility import EMISSION_FACTORS


class Country(BaseUserModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=2, unique=True)
    region = models.CharField(max_length=10, blank=True, default='')
    currency_code = models.CharField(max_length=3, blank=True, default='')
    currency_name = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        db_table = "COUNTRY_MASTER"
        verbose_name = "Country Master"
        verbose_name_plural = "Country Master"
        ordering = ['id']


class PortOfLoading(BaseUserModel):
    name = models.CharField(max_length=50, blank=True, null=True)
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    country = models.PositiveIntegerField()
    unlocode = models.CharField(max_length=50, unique=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    supplyx_code = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "Port of Loading"
        verbose_name_plural = "Ports of Loading"
        ordering = ['name']
        db_table = "PORT_OF_LOADING"


class PortOfDestination(BaseUserModel):
    name = models.CharField(max_length=50, blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    country = models.PositiveIntegerField()
    unlocode = models.CharField(max_length=50)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    supplyx_code = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "Port of Destination"
        verbose_name_plural = "Ports of Destination"
        ordering = ['name']
        db_table = "PORT_OF_DESTINATION"


class Carrier(BaseUserModel):
    name = models.CharField(max_length=100)
    carrier_code = models.CharField(max_length=50)
    transportation_mode = models.PositiveIntegerField()
    fuel_type = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "CARRIER"
        verbose_name = "Carrier"
        verbose_name_plural = "Carriers"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def emission_factor(self):
        return EMISSION_FACTORS.get(self.fuel_type)


class TransportMode(BaseUserModel):
    """
    Master table to store different transport modes.
    Example: Air, Sea, Road, Rail.
    """
    mode_name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "TRANSPORT_MODE"
        ordering = ['-created_on']


class ShipmentType(BaseUserModel):
    """
    Master table to store types of shipments.
    Example: FCL, LCL, Courier, Express.
    """
    mode = models.PositiveIntegerField()
    shipment_type_name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "SHIPMENT_TYPE"
        verbose_name = "Shipment Type"
        verbose_name_plural = "Shipment Types"
        ordering = ['shipment_type_name']


class EquipmentType(BaseUserModel):
    """
    Master table to store types of transport equipment.
    Example: 20FT Container, 40FT Container, Flat Rack, Reefer.
    """
    mode = models.ForeignKey(
        TransportMode,
        on_delete=models.CASCADE,
        related_name="equipment_types"
    )
    equipment_name = models.CharField(max_length=50)
    equipment_category = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    iso_code = models.CharField(max_length=50, blank=True, null=True)
    supplyx_code = models.CharField(max_length=50, blank=True, null=True)
    equipment_size = models.CharField(max_length=50, blank=True, null=True)
    equipment_height = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "EQUIPMENT_TYPE"
        verbose_name = "Equipment Type"
        verbose_name_plural = "Equipment Types"
        ordering = ['equipment_name']


class Incoterm(BaseUserModel):
    """
    Master table to store INCOTERM (International Commercial Terms) data.
    Example: EXW, FOB, FCA, DAP, etc.
    """
    incoterm_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "INCOTERM"
        verbose_name = "Incoterm"
        verbose_name_plural = "Incoterms"
        ordering = ['incoterm_name']


class StatusTransition(BaseUserModel):
    status_from = models.PositiveIntegerField(db_column="STATUS_FROM")
    status_to = models.PositiveIntegerField(db_column="STATUS_TO")
    is_active = models.BooleanField(default=True, db_column="IS_ACTIVE")

    class Meta:
        db_table = "STATUS_TRANSITION"


class Company(BaseUserModel):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    company_type = models.PositiveIntegerField()
    country = models.PositiveIntegerField()
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    parent_company = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    optionals = models.JSONField(default=list, blank=True)
    supplyx_code = models.CharField(max_length=250, null=True, blank=True)
    contact_person = models.CharField(max_length=100)
    address = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "COMPANY"
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name
