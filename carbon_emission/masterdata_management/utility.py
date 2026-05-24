from django.db.models import Value, Q
from django.db.models.functions import Concat
import re
# from shipment_management.utility import TransportModeEnum, parse_search_date, parse_year_month, parse_day_month
from django.db.models import Q, Subquery

from decimal import Decimal, InvalidOperation
from rest_framework import serializers

from masterdata_management.models import Company
from shipment_management.utility import TransportModeEnum


def get_company_info():
    """
    Returns a company .
    """
    queryset = Company.objects.values('id', 'name')
    company_dict = {c['id']: c['name'] for c in queryset}
    return company_dict


def validate_decimal_coordinate(value, field_name: str, min_val: float, max_val: float):
    """
    Validates a decimal coordinate value( latitude or longitude )
    - Allows None (for nullable fields)
    - Checks numeric validity
    - Ensures within range
    - Enforces up to 6 decimal places
    """

    if value is None:
        return

    try:
        dec_value = Decimal(value)
    except (InvalidOperation, TypeError):
        raise serializers.ValidationError(
            {field_name: f"{field_name.capitalize()} must be a valid decimal number."}
        )

    if dec_value < Decimal(str(min_val)) or dec_value > Decimal(str(max_val)):
        raise serializers.ValidationError(
            {field_name: f"{field_name.capitalize()} must be between {min_val} and {max_val}."}
        )

    parts = str(dec_value).split('.')
    if len(parts) == 2 and len(parts[1]) > 6:
        raise serializers.ValidationError(
            {field_name: f"{field_name.capitalize()} cannot have more than 6 decimal places."}
        )


def build_port_global_search_q(search_value):
    """
    Builds a global OR-based search for PortOfLoading.
    """

    q = Q()

    if not search_value:
        return q

    search_value = str(search_value).strip()
    search_lower = search_value.lower()

    if not search_value:
        return q

    # ------------------------
    # TEXT FIELDS
    # ------------------------
    q |= Q(name__icontains=search_value)
    q |= Q(code__icontains=search_value)
    q |= Q(country__icontains=search_value)
    q |= Q(unlocode__icontains=search_value)
    q |= Q(timezone__icontains=search_value)
    q |= Q(address__icontains=search_value)
    q |= Q(description__icontains=search_value)
    q |= Q(supplyx_code__icontains=search_value)

    # ------------------------
    # NUMERIC SEARCH (optional)
    # ------------------------
    try:
        float_value = float(search_value)
        q |= Q(latitude=float_value)
        q |= Q(longitude=float_value)
    except ValueError:
        pass

    # ---------------- BOOLEAN ----------------
    if search_lower in ("active", "true"):
        q |= Q(is_active=True)
    elif search_lower in ("inactive", "false"):
        q |= Q(is_active=False)

    return q


def build_company_global_search_q(search_value):
    """
    Builds a global search Q object for Company model.
    """
    if not search_value:
        return Q()

    search_value = search_value.strip()
    search_lower = search_value.lower()
    if not search_value:
        return Q()

    q = Q()

    text_fields = [
        "name",
        "short_name",
        "country",
        "email",
        "phone",
        "supplyx_code",
        "contact_person",
        "address",
        "parent_company"
    ]

    for field in text_fields:
        q |= Q(**{f"{field}__icontains": search_value})

    # Numeric search
    if search_value.isdigit():
        q |= Q(company_type=int(search_value))
        q |= Q(parent_company=int(search_value))

    # ---------------- BOOLEAN ----------------
    if search_lower in ("active", "true"):
        q |= Q(is_active=True)
    elif search_lower in ("inactive", "false"):
        q |= Q(is_active=False)

    return q


def build_carrier_global_search_q(search_value):
    """
    Builds a global search Q object for Carrier model.
    Handles ENUM-based transportation_mode correctly.
    """
    q = Q()

    if not search_value:
        return q

    search_value = search_value.strip()
    search_lower = search_value.lower()
    if not search_value:
        return q

    search_upper = search_value.upper()
    search_lower = search_value.lower()

    # ---------- TEXT SEARCH ----------
    text_fields = [
        "name",
        "carrier_code",
        "description",
        "supplyx_code",
    ]

    for field in text_fields:
        q |= Q(**{f"{field}__icontains": search_value})

    # ---------- ENUM NAME SEARCH ----------
    for enum_member in TransportModeEnum:
        if search_lower in enum_member.DESCRIPTION.lower():
            q |= Q(transportation_mode=enum_member.CODE)

    # ---------- ENUM CODE SEARCH ----------
    if search_value.isdigit():
        q |= Q(transportation_mode=int(search_value))

    # ---------- BOOLEAN SEARCH ----------
    if search_upper in ("ACTIVE", "TRUE", "YES"):
        q |= Q(is_active=True)
    elif search_upper in ("INACTIVE", "FALSE", "NO"):
        q |= Q(is_active=False)

    return q


def build_role_global_search_q(search_value):
    q = Q()
    if not search_value:
        return q

    search_value = search_value.strip()

    # -------- TEXT SEARCH --------
    q |= Q(role_name__icontains=search_value)
    q |= Q(role_description__icontains=search_value)

    # -------- INTEGER SEARCH --------
    if search_value.isdigit():
        int_value = int(search_value)
        q |= Q(created_by=int_value)
        q |= Q(modified_by=int_value)

        # Year search
        if len(search_value) == 4:
            q |= Q(created_on__year=int_value)
            q |= Q(modified_on__year=int_value)

        if search_value.isdigit() and len(search_value) == 2:
            int_value = int(search_value)

            # Month: 01–12
            if 1 <= int_value <= 12:
                q |= Q(created_on__month=int_value)
                q |= Q(modified_on__month=int_value)

            # Day: 01–31
            if 1 <= int_value <= 31:
                q |= Q(created_on__day=int_value)
                q |= Q(modified_on__day=int_value)

    # ---------------- YEAR-MONTH ----------------
    ym = parse_year_month(search_value)
    if ym:
        if ym:
            year, month = ym
            q |= Q(created_on__year=year, created_on__month=month)
            q |= Q(modified_on__year=year, modified_on__month=month)

    # ---------------- DAY-MONTH (DD/MM) ----------------
    dm = parse_day_month(search_value)
    if dm:
        month, day = dm
        q |= Q(created_on__month=month, created_on__day=day)
        q |= Q(modified_on__month=month, modified_on__day=day)

    # ---------------- FULL DATE ----------------
    try:
        parsed_date = parse_search_date(search_value)
        q |= Q(created_on__date=parsed_date)
        q |= Q(modified_on__date=parsed_date)
    except ValueError:
        pass



    return q


def build_customer_company_global_search_q(search_value):
    q = Q()
    if not search_value:
        return q

    search_value = search_value.strip()
    search_lower = search_value.lower()

    # ---------------- TEXT SEARCH ----------------
    q |= Q(company__name__icontains=search_value)
    q |= Q(customer_company__name__icontains=search_value)

    # ---------------- BOOLEAN ----------------
    if search_lower in ("active", "true"):
        q |= Q(is_active=True)
    elif search_lower in ("inactive", "false"):
        q |= Q(is_active=False)

    return q
