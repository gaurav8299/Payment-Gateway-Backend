from common.views import (
    HealthCheckView,
    LivenessCheckView,
    ReadinessCheckView,
    VersionInfoView,
)
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # ── Bonus System APIs ───────────────────────────
    path("api/v1/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/v1/ready/", ReadinessCheckView.as_view(), name="readiness-check"),
    path("api/v1/live/", LivenessCheckView.as_view(), name="liveness-check"),
    path("api/v1/version/", VersionInfoView.as_view(), name="version-info"),
    # ── Accounts & Authentication APIs ──────────────
    path("api/v1/auth/", include("accounts.urls", namespace="accounts")),
    # ── Merchant Management APIs ────────────────────
    path("api/v1/merchants/", include("merchant.urls", namespace="merchant")),
    # ── Customer Management APIs ────────────────────
    path("api/v1/customers/", include("customer.urls", namespace="customer")),
    # ── Order Management APIs ───────────────────────
    path("api/v1/orders/", include("orders.urls", namespace="orders")),
    # ── Digital Wallet APIs ─────────────────────────
    path("api/v1/wallets/", include("wallet.urls", namespace="wallet")),
    # ── Payment Engine APIs ─────────────────────────
    path("api/v1/payments/", include("payments.urls", namespace="payments")),
    # ── Refund System APIs ──────────────────────────
    path("api/v1/refunds/", include("refunds.urls", namespace="refunds")),
    # ── Webhook Engine APIs ─────────────────────────
    path("api/v1/webhooks/", include("webhooks.urls", namespace="webhooks")),
    # ── Audit Logs APIs ─────────────────────────────
    path("api/v1/audit-logs/", include("audit_logs.urls", namespace="audit_logs")),
    # ── Notifications System APIs ───────────────────
    path(
        "api/v1/notifications/",
        include("notifications.urls", namespace="notifications"),
    ),
    # ── Analytics, Reports, Invoices & Coupons APIs ─
    path("api/v1/analytics/", include("analytics.urls", namespace="analytics")),
    # ── OpenAPI Schema & Swagger Documentation ──────
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
