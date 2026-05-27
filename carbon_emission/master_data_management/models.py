from django.db import models


# Create your models here.
class Country(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=2, unique=True)
    region = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "COUNTRY"


class Location(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, null=True, blank=True)
    unlocode = models.CharField(max_length=20, null=True, blank=True)
    iata_code = models.CharField(max_length=10, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    address = models.TextField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    location_type = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "LOCATION"


class Carrier(models.Model):
    name = models.CharField(max_length=100)
    carrier_code = models.CharField(max_length=50, unique=True)
    transportation_mode = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "CARRIER"

class Company(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    company_type = models.PositiveIntegerField()
    country = models.PositiveIntegerField()
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    parent_company = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    address = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "COMPANY"
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name
