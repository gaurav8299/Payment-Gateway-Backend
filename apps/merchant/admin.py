from django.contrib import admin
from merchant.models import (
    MerchantAPIKey,
    MerchantProfile,
    MerchantWebhookSecret,
    WebhookEndpoint,
)


@admin.register(MerchantProfile)
class MerchantProfileAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "user",
        "status",
        "country",
        "currency",
        "created_at",
    )
    list_filter = ("status", "country", "currency")
    search_fields = (
        "business_name",
        "legal_business_name",
        "user__email",
        "gst_number",
        "pan_number",
    )


@admin.register(MerchantAPIKey)
class MerchantAPIKeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "merchant",
        "publishable_key",
        "secret_key_prefix",
        "is_active",
        "last_used_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "merchant__business_name", "publishable_key")


@admin.register(MerchantWebhookSecret)
class MerchantWebhookSecretAdmin(admin.ModelAdmin):
    list_display = ("merchant", "secret_prefix", "is_active", "created_at")


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ("url", "merchant", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("url", "merchant__business_name")
