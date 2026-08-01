from decimal import Decimal

from merchant.validators import validate_currency
from orders.models import Order, OrderEvent
from rest_framework import serializers


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "merchant",
            "customer",
            "amount",
            "currency",
            "description",
            "metadata",
            "status",
            "expires_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "merchant",
            "status",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    currency = serializers.CharField(
        max_length=3, default="INR", validators=[validate_currency]
    )
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    metadata = serializers.JSONField(required=False, default=dict)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class OrderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEvent
        fields = ["id", "event_type", "payload", "created_at"]
        read_only_fields = fields
