import uuid

from common.models import TimeStampedModel
from customer.models import CustomerProfile
from django.db import models
from merchant.models import MerchantProfile


class WalletStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    FROZEN = "FROZEN", "Frozen"
    CLOSED = "CLOSED", "Closed"


class WalletTransactionType(models.TextChoices):
    CREDIT = "CREDIT", "Credit"
    DEBIT = "DEBIT", "Debit"
    REFUND = "REFUND", "Refund"
    PAYMENT = "PAYMENT", "Payment"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    REVERSAL = "REVERSAL", "Reversal"


class WalletTransactionStatus(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class Wallet(TimeStampedModel):
    """
    Digital Wallet entity owned by a Customer under a specific Merchant context.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.CASCADE, related_name="wallets", db_index=True
    )
    merchant = models.ForeignKey(
        MerchantProfile, on_delete=models.CASCADE, related_name="wallets", db_index=True
    )
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, db_index=True
    )
    currency = models.CharField(max_length=3, default="INR", db_index=True)
    status = models.CharField(
        max_length=20,
        choices=WalletStatus.choices,
        default=WalletStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        db_table = "customer_wallets"
        unique_together = ("customer", "merchant", "currency")
        verbose_name = "Digital Wallet"
        verbose_name_plural = "Digital Wallets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "merchant", "currency"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Wallet ({self.customer.name}) - {self.balance} {self.currency} [{self.status}]"


class WalletTransaction(models.Model):
    """
    Immutable Financial Audit Ledger for all Wallet balance mutations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_number = models.CharField(
        max_length=100, unique=True, db_index=True
    )  # txn_xxxx
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions", db_index=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(
        max_length=20, choices=WalletTransactionType.choices, db_index=True
    )
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=WalletTransactionStatus.choices,
        default=WalletTransactionStatus.SUCCESS,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "wallet_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "type", "created_at"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.transaction_number} [{self.type}]: {self.amount} ({self.status})"
