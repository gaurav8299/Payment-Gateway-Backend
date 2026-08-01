from django.urls import path
from merchant.views import (
    MerchantAPIKeyListCreateView,
    MerchantAPIKeyRevokeView,
    MerchantProfileView,
    MerchantStatsView,
    WebhookEndpointDetailView,
    WebhookEndpointListCreateView,
    WebhookSecretRotateView,
)

app_name = "merchant"

urlpatterns = [
    path("me/", MerchantProfileView.as_view(), name="merchant_profile"),
    path("me/stats/", MerchantStatsView.as_view(), name="merchant_stats"),
    path(
        "api-keys/", MerchantAPIKeyListCreateView.as_view(), name="api_key_list_create"
    ),
    path(
        "api-keys/<uuid:key_id>/revoke/",
        MerchantAPIKeyRevokeView.as_view(),
        name="api_key_revoke",
    ),
    path(
        "webhook-secret/rotate/",
        WebhookSecretRotateView.as_view(),
        name="webhook_secret_rotate",
    ),
    path(
        "webhook-endpoints/",
        WebhookEndpointListCreateView.as_view(),
        name="webhook_endpoint_list_create",
    ),
    path(
        "webhook-endpoints/<uuid:endpoint_id>/",
        WebhookEndpointDetailView.as_view(),
        name="webhook_endpoint_detail",
    ),
]
