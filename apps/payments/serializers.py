from decimal import Decimal

from merchant.validators import validate_currency
from payments.models import Payment, PaymentGateway, PaymentLedger, PaymentMethod
from rest_framework import serializers


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_id",
            "order",
            "merchant",
            "customer",
            "wallet",
            "gateway",
            "gateway_transaction_id",
            "amount",
            "currency",
            "payment_method",
            "status",
            "failure_code",
            "failure_reason",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "payment_id",
            "merchant",
            "customer",
            "wallet",
            "status",
            "created_at",
            "updated_at",
        ]


class PaymentCreateSerializer(serializers.Serializer):
    order_id = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    currency = serializers.CharField(
        max_length=3, default="INR", validators=[validate_currency]
    )
    gateway = serializers.ChoiceField(
        choices=PaymentGateway.choices, default=PaymentGateway.DUMMY
    )
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices, default=PaymentMethod.CARD
    )
    metadata = serializers.JSONField(required=False, default=dict)


class PaymentLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLedger
        fields = ["id", "action", "amount", "status", "gateway_response", "created_at"]
        read_only_fields = fields
