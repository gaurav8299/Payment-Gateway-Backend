from customer.models import (
    CardBrand,
    CustomerProfile,
    PaymentMethodType,
    SavedPaymentMethod,
)
from rest_framework import serializers


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CustomerCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class AddMockPaymentMethodSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=PaymentMethodType.choices, default=PaymentMethodType.CARD
    )
    raw_card_number = serializers.CharField(
        max_length=19, required=False, write_only=True
    )
    card_brand = serializers.ChoiceField(
        choices=CardBrand.choices, default=CardBrand.VISA, required=False
    )
    exp_month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    exp_year = serializers.IntegerField(min_value=2024, max_value=2050, required=False)
    upi_id = serializers.CharField(max_length=100, required=False)
    wallet_provider = serializers.CharField(max_length=50, required=False)
    is_default = serializers.BooleanField(default=False)


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPaymentMethod
        fields = [
            "id",
            "type",
            "card_token",
            "masked_card_number",
            "card_brand",
            "exp_month",
            "exp_year",
            "upi_id",
            "wallet_provider",
            "is_default",
            "created_at",
        ]
        read_only_fields = fields
