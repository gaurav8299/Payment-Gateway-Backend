from django.contrib import admin
from payments.models import Payment, PaymentEvent, PaymentLedger


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_id",
        "order",
        "merchant",
        "gateway",
        "amount",
        "currency",
        "payment_method",
        "status",
        "created_at",
    )
    list_filter = ("status", "gateway", "payment_method", "currency")
    search_fields = (
        "payment_id",
        "gateway_transaction_id",
        "order__order_number",
        "merchant__business_name",
    )


@admin.register(PaymentLedger)
class PaymentLedgerAdmin(admin.ModelAdmin):
    list_display = ("payment", "action", "amount", "status", "created_at")
    list_filter = ("action", "status")
    search_fields = ("payment__payment_id", "action")


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ("payment", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("payment__payment_id", "event_type")
