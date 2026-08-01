from django.contrib import admin
from orders.models import Order, OrderEvent


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "merchant",
        "customer",
        "amount",
        "currency",
        "status",
        "expires_at",
        "created_at",
    )
    list_filter = ("status", "currency")
    search_fields = (
        "order_number",
        "merchant__business_name",
        "customer__email",
        "description",
    )


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("order", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("order__order_number", "event_type")
