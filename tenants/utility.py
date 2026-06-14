import threading

_thread_local = threading.local()


def set_current_tenant(tenant):
    _thread_local.tenant = tenant


def get_current_tenant():
    return getattr(_thread_local, "tenant", None)


def clear_current_tenant():
    _thread_local.tenant = None

from django.db import models
from .context import get_current_tenant


class TenantQuerySet(models.QuerySet):
    def for_current_tenant(self):
        tenant = get_current_tenant()
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_current_tenant(self):
        return self.get_queryset().for_current_tenant()


class TenantAwareModel(models.Model):
    """
    Abstract base — inherit this in any model that must be
    scoped to a tenant (Segment, SegmentEmission, etc.).
    """
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True

