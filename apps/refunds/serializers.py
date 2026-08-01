from decimal import Decimal

from refunds.models import Refund, RefundLedger
from rest_framework import serializers


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "id",
            "refund_id",
            "payment",
            "order",
            "merchant",
            "customer",
            "amount",
            "currency",
            "reason",
            "status",
            "failure_code",
            "failure_reason",
            "gateway_refund_id",
            "metadata",
            "requested_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "refund_id",
            "payment",
            "order",
            "merchant",
            "customer",
            "currency",
            "status",
            "failure_code",
            "failure_reason",
            "gateway_refund_id",
            "requested_by",
            "created_at",
            "updated_at",
        ]


class RefundCreateSerializer(serializers.Serializer):
    payment_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class RefundLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundLedger
        fields = ["id", "action", "amount", "status", "gateway_response", "created_at"]
        read_only_fields = fields
