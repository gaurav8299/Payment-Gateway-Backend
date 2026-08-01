from customer.models import CustomerProfile, SavedPaymentMethod
from django.contrib import admin


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "merchant", "created_at")
    search_fields = ("name", "email", "phone", "merchant__business_name")
    list_filter = ("merchant",)


@admin.register(SavedPaymentMethod)
class SavedPaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "type",
        "card_brand",
        "masked_card_number",
        "card_token",
        "is_default",
        "created_at",
    )
    list_filter = ("type", "card_brand", "is_default")
    search_fields = (
        "customer__name",
        "customer__email",
        "card_token",
        "masked_card_number",
        "upi_id",
    )
