from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Tenant, TenantUser
from .serializer import TenantLoginSerializer


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="X-Tenant-ID",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Your tenant UUID",
        )
    ],
    request=TenantLoginSerializer,
    responses={200: dict},
    summary="Login and get JWT token",
)
class TenantLoginView(APIView):
    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            try:
                request.tenant = Tenant.objects.get(id=tenant_id, is_active=True)
            except Tenant.DoesNotExist:
                request.tenant = None
        else:
            request.tenant = None
        super().initial(request, *args, **kwargs)

    def post(self, request):
        serializer = TenantLoginSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        refresh["tenant_id"] = str(user.tenant_id) if user.tenant_id else None

        return Response({
            "access":    str(refresh.access_token),
            "refresh":   str(refresh),
            "tenant_id": str(request.tenant.id),
            "role":      user.role,
        })


class TenantTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)