from django.http import JsonResponse
from .models import Tenant
from .context import set_current_tenant, clear_current_tenant


class TenantMiddleware:

    PUBLIC_PATHS = [
        "/api/auth/login/",
        "/api/auth/token/refresh/",
        "/api/schema/",
        "/api/swagger/",
        "/admin/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Always clear first to prevent thread bleed
        clear_current_tenant()

        if any(request.path.startswith(p) for p in self.PUBLIC_PATHS):
            return self.get_response(request)

        tenant_id = request.headers.get("X-Tenant-ID")

        if not tenant_id:
            return JsonResponse(
                {"detail": "X-Tenant-ID header is required."},
                status=400,
            )

        try:
            tenant = Tenant.objects.get(id=tenant_id, is_active=True)
        except (Tenant.DoesNotExist, Exception):
            return JsonResponse(
                {"detail": "Invalid or inactive tenant."},
                status=403,
            )

        set_current_tenant(tenant)
        request.tenant = tenant

        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant()

        return response