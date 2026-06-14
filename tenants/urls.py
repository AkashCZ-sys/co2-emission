from django.urls import path
from .views import TenantLoginView, TenantTokenRefreshView

urlpatterns = [
    path("auth/login/", TenantLoginView.as_view(), name="tenant-login"),
    path("auth/token/refresh/", TenantTokenRefreshView.as_view(), name="token-refresh"),
]