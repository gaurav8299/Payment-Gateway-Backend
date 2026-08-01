import uuid

from common.models import SoftDeleteModel, TimeStampedModel
from django.db import models
from merchant.models import MerchantProfile


class CustomerProfile(TimeStampedModel, SoftDeleteModel):
    """
    Customer Entity associated with a specific Merchant.
    Enforces strict Merchant isolation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="customers",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "customer_profiles"
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"
        unique_together = ("merchant", "email")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.merchant.business_name}"


class PaymentMethodType(models.TextChoices):
    CARD = "CARD", "Card"
    UPI = "UPI", "UPI"
    WALLET = "WALLET", "Wallet"


class CardBrand(models.TextChoices):
    VISA = "VISA", "Visa"
    MASTERCARD = "MASTERCARD", "MasterCard"
    RUPAY = "RUPAY", "RuPay"
    AMEX = "AMEX", "American Express"


class SavedPaymentMethod(TimeStampedModel):
    """
    Mock Tokenized Saved Payment Method. Raw card numbers are NEVER stored.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.CASCADE, related_name="payment_methods"
    )
    type = models.CharField(
        max_length=20, choices=PaymentMethodType.choices, default=PaymentMethodType.CARD
    )
    card_token = models.CharField(
        max_length=100, unique=True, db_index=True
    )  # card_token_xxxx
    masked_card_number = models.CharField(
        max_length=30, blank=True
    )  # 4242 **** **** 4242
    card_brand = models.CharField(
        max_length=20, choices=CardBrand.choices, default=CardBrand.VISA, blank=True
    )
    exp_month = models.IntegerField(null=True, blank=True)
    exp_year = models.IntegerField(null=True, blank=True)
    fingerprint = models.CharField(max_length=128, blank=True)
    upi_id = models.CharField(max_length=100, null=True, blank=True)
    wallet_provider = models.CharField(max_length=50, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "customer_saved_payment_methods"
        ordering = ["-created_at"]

    def __str__(self):
        if self.type == PaymentMethodType.CARD:
            return f"{self.card_brand} {self.masked_card_number}"
        elif self.type == PaymentMethodType.UPI:
            return f"UPI ({self.upi_id})"
        return f"Wallet ({self.wallet_provider})"
