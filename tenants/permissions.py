from rest_framework.permissions import BasePermission


class IsTenantAuthenticated(BasePermission):
    message = "Authentication required or tenant mismatch."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            return False
        return request.user.tenant_id == tenant.id


class IsTenantAdmin(IsTenantAuthenticated):
    message = "Admin role required."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.is_superuser or request.user.role == "ADMIN"