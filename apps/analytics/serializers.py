from orders.models import Coupon, Invoice
from rest_framework import serializers


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "merchant",
            "discount_type",
            "discount_value",
            "max_discount_amount",
            "min_order_amount",
            "usage_limit",
            "used_count",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "used_count", "created_at"]


class CouponCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FIXED"], default="PERCENTAGE"
    )
    discount_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    max_discount_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    min_order_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=0.00
    )
    usage_limit = serializers.IntegerField(required=False, default=100)


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class InvoiceSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    merchant_name = serializers.CharField(
        source="merchant.business_name", read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "order_number",
            "merchant_name",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "currency",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class MerchantReportFilterSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(
        choices=["revenue", "refund", "order", "customer", "wallet", "transaction"],
        default="revenue",
    )
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    status = serializers.CharField(required=False)
    currency = serializers.CharField(required=False, max_length=3)
    payment_method = serializers.CharField(required=False)
    gateway = serializers.CharField(required=False)
    export_format = serializers.ChoiceField(
        choices=["json", "csv"], required=False, default="json"
    )


class ChartFilterSerializer(serializers.Serializer):
    granularity = serializers.ChoiceField(
        choices=["hourly", "daily", "weekly", "monthly"], default="daily"
    )
    days = serializers.IntegerField(
        required=False, default=30, min_value=1, max_value=365
    )
