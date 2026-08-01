from django.contrib import admin
from refunds.models import DeadLetterRefundTask, Refund, RefundEvent, RefundLedger


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        "refund_id",
        "payment",
        "merchant",
        "amount",
        "currency",
        "status",
        "gateway_refund_id",
        "created_at",
    )
    list_filter = ("status", "currency")
    search_fields = (
        "refund_id",
        "gateway_refund_id",
        "payment__payment_id",
        "merchant__business_name",
    )


@admin.register(RefundLedger)
class RefundLedgerAdmin(admin.ModelAdmin):
    list_display = ("refund", "action", "amount", "status", "created_at")
    list_filter = ("action", "status")
    search_fields = ("refund__refund_id", "action")


@admin.register(RefundEvent)
class RefundEventAdmin(admin.ModelAdmin):
    list_display = ("refund", "event_type", "created_at")
    list_filter = ("event_type",)
    search_fields = ("refund__refund_id", "event_type")


@admin.register(DeadLetterRefundTask)
class DeadLetterRefundTaskAdmin(admin.ModelAdmin):
    list_display = ("refund", "retry_count", "resolved", "created_at")
    list_filter = ("resolved",)
    search_fields = ("refund__refund_id", "error_message")
