from decimal import Decimal

from rest_framework import serializers
from wallet.models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            "id",
            "customer",
            "merchant",
            "balance",
            "currency",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "merchant",
            "balance",
            "status",
            "created_at",
            "updated_at",
        ]


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "transaction_number",
            "wallet",
            "amount",
            "type",
            "balance_before",
            "balance_after",
            "reference",
            "description",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class WalletCreditDebitSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
