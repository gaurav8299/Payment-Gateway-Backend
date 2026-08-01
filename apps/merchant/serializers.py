from merchant.models import (
    MerchantAPIKey,
    MerchantProfile,
    WebhookEndpoint,
    WebhookEventTypes,
)
from merchant.validators import (
    validate_currency,
    validate_gst_number,
    validate_pan_number,
)
from rest_framework import serializers


class MerchantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantProfile
        fields = [
            "id",
            "business_name",
            "legal_business_name",
            "business_type",
            "merchant_category_code",
            "gst_number",
            "pan_number",
            "website",
            "support_email",
            "support_phone",
            "logo_url",
            "address",
            "country",
            "currency",
            "timezone",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class MerchantProfileUpdateSerializer(serializers.ModelSerializer):
    gst_number = serializers.CharField(
        validators=[validate_gst_number], required=False, allow_blank=True
    )
    pan_number = serializers.CharField(
        validators=[validate_pan_number], required=False, allow_blank=True
    )
    currency = serializers.CharField(validators=[validate_currency], required=False)

    class Meta:
        model = MerchantProfile
        fields = [
            "business_name",
            "legal_business_name",
            "business_type",
            "merchant_category_code",
            "gst_number",
            "pan_number",
            "website",
            "support_email",
            "support_phone",
            "logo_url",
            "address",
            "country",
            "currency",
            "timezone",
        ]


class CreateAPIKeySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, default="Default Live Key")


class MerchantAPIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantAPIKey
        fields = [
            "id",
            "name",
            "publishable_key",
            "secret_key_prefix",
            "is_active",
            "last_used_at",
            "expires_at",
            "created_at",
        ]
        read_only_fields = fields


class WebhookEndpointSerializer(serializers.ModelSerializer):
    enabled_events = serializers.ListField(
        child=serializers.ChoiceField(choices=WebhookEventTypes.choices)
    )

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "url",
            "description",
            "enabled_events",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
