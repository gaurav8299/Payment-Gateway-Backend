from django.urls import path
from webhooks.views import (
    WebhookDeliveryListView,
    WebhookEndpointDetailView,
    WebhookEndpointListCreateView,
    WebhookEventListView,
    WebhookReplayView,
    WebhookSecretRotateView,
    WebhookTestPingView,
)

app_name = "webhooks"

urlpatterns = [
    path(
        "endpoints/",
        WebhookEndpointListCreateView.as_view(),
        name="endpoint_list_create",
    ),
    path(
        "endpoints/<str:endpoint_id>/",
        WebhookEndpointDetailView.as_view(),
        name="endpoint_detail",
    ),
    path(
        "endpoints/<str:endpoint_id>/rotate-secret/",
        WebhookSecretRotateView.as_view(),
        name="endpoint_rotate_secret",
    ),
    path(
        "endpoints/<str:endpoint_id>/test/",
        WebhookTestPingView.as_view(),
        name="endpoint_test_ping",
    ),
    path("events/", WebhookEventListView.as_view(), name="event_list"),
    path("deliveries/", WebhookDeliveryListView.as_view(), name="delivery_list"),
    path(
        "deliveries/<str:delivery_id>/replay/",
        WebhookReplayView.as_view(),
        name="delivery_replay",
    ),
]
