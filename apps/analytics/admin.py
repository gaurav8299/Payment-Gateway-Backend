from django.contrib import admin
from orders.models import Coupon, Invoice


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "merchant",
        "discount_type",
        "discount_value",
        "usage_limit",
        "used_count",
        "status",
        "created_at",
    )
    list_filter = ("discount_type", "status")
    search_fields = ("code",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "order",
        "merchant",
        "total_amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "currency")
    search_fields = ("invoice_number",)
