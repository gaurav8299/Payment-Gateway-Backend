from django.contrib import admin
from webhooks.models import OutboxEvent, WebhookDelivery, WebhookEndpoint, WebhookEvent


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ("endpoint_id", "merchant", "name", "url", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("endpoint_id", "name", "url", "merchant__business_name")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "merchant",
        "event_type",
        "resource_type",
        "resource_id",
        "status",
        "created_at",
    )
    list_filter = ("event_type", "status")
    search_fields = ("event_id", "resource_id", "merchant__business_name")


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "delivery_id",
        "endpoint",
        "http_status",
        "attempt_number",
        "duration_ms",
        "status",
        "delivered_at",
    )
    list_filter = ("status", "http_status")
    search_fields = ("delivery_id", "endpoint__url")


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "merchant",
        "event_type",
        "processed",
        "processed_at",
        "created_at",
    )
    list_filter = ("processed", "event_type")
    search_fields = ("event_id", "resource_id")
