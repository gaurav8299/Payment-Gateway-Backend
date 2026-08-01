from rest_framework import serializers
from webhooks.models import WebhookDelivery, WebhookEndpoint, WebhookEvent


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "endpoint_id",
            "merchant",
            "name",
            "url",
            "status",
            "enabled_events",
            "api_version",
            "description",
            "last_delivery_at",
            "last_success_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "endpoint_id",
            "merchant",
            "status",
            "last_delivery_at",
            "last_success_at",
            "created_at",
            "updated_at",
        ]


class WebhookEndpointCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    url = serializers.URLField(max_length=500)
    enabled_events = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=lambda: ["*"],
    )
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    api_version = serializers.CharField(max_length=20, default="v1")


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = [
            "id",
            "event_id",
            "merchant",
            "event_type",
            "resource_type",
            "resource_id",
            "payload",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "delivery_id",
            "event",
            "endpoint",
            "http_status",
            "response_body",
            "attempt_number",
            "duration_ms",
            "status",
            "error_message",
            "delivered_at",
        ]
        read_only_fields = fields
