from django.contrib.auth import authenticate
from rest_framework import serializers


class TenantLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        request = self.context["request"]
        tenant = getattr(request, "tenant", None)

        if tenant is None:
            raise serializers.ValidationError(
                "X-Tenant-ID header is required for authentication."
            )

        user = authenticate(
            request=request,
            username=data["username"],
            password=data["password"],
        )

        if user is None:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        if not user.is_superuser and user.tenant_id != tenant.id:
            raise serializers.ValidationError(
                "User does not belong to this tenant."
            )

        data["user"] = user
        return data