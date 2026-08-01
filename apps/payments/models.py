import uuid

from common.models import SoftDeleteModel, TimeStampedModel
from customer.models import CustomerProfile
from django.db import models
from merchant.models import MerchantProfile
from orders.models import Order
from wallet.models import Wallet


class PaymentStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    AUTHORIZED = "AUTHORIZED", "Authorized"
    CAPTURED = "CAPTURED", "Captured"
    SETTLED = "SETTLED", "Settled"
    FAILED = "FAILED", "Failed"
    VOIDED = "VOIDED", "Voided"


class PaymentMethod(models.TextChoices):
    CARD = "CARD", "Card"
    UPI = "UPI", "UPI"
    NETBANKING = "NETBANKING", "Net Banking"
    WALLET = "WALLET", "Wallet"
    COD = "COD", "Cash On Delivery"


class PaymentGateway(models.TextChoices):
    DUMMY = "DUMMY", "Dummy Gateway"
    STRIPE = "STRIPE", "Stripe Gateway"
    RAZORPAY = "RAZORPAY", "Razorpay Gateway"
    WALLET = "WALLET", "Digital Wallet"
    COD = "COD", "Cash On Delivery"


class Payment(TimeStampedModel, SoftDeleteModel):
    """
    Payment Entity representing financial transactions against an Order.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_id = models.CharField(
        max_length=100, unique=True, db_index=True
    )  # pay_xxxx
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payments", db_index=True
    )
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True,
    )
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
        db_index=True,
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
        db_index=True,
    )
    gateway = models.CharField(
        max_length=50,
        choices=PaymentGateway.choices,
        default=PaymentGateway.DUMMY,
        db_index=True,
    )
    gateway_transaction_id = models.CharField(max_length=100, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    currency = models.CharField(max_length=3, default="INR", db_index=True)
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CARD,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CREATED,
        db_index=True,
    )
    failure_code = models.CharField(max_length=50, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "status", "created_at"]),
            models.Index(fields=["order", "status"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["gateway", "gateway_transaction_id"]),
        ]

    def __str__(self):
        return f"{self.payment_id} - {self.amount} {self.currency} [{self.status}]"


class PaymentLedgerAction(models.TextChoices):
    PAYMENT_CREATED = "PAYMENT_CREATED", "Payment Created"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED", "Payment Authorized"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED", "Payment Captured"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
    PAYMENT_VOIDED = "PAYMENT_VOIDED", "Payment Voided"
    PAYMENT_SETTLED = "PAYMENT_SETTLED", "Payment Settled"


class PaymentLedger(models.Model):
    """
    Immutable Financial Audit Ledger for every Payment action.
    Entries must NEVER be updated or deleted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="ledger_entries", db_index=True
    )
    action = models.CharField(
        max_length=50, choices=PaymentLedgerAction.choices, db_index=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "payment_ledger"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} -> {self.payment.payment_id} ({self.status})"


class PaymentEventType(models.TextChoices):
    CREATED = "payment.created", "Payment Created"
    AUTHORIZED = "payment.authorized", "Payment Authorized"
    CAPTURED = "payment.captured", "Payment Captured"
    FAILED = "payment.failed", "Payment Failed"
    VOIDED = "payment.voided", "Payment Voided"
    SETTLED = "payment.settled", "Payment Settled"


class PaymentEvent(TimeStampedModel):
    """
    Domain Event Log tracking payment state changes for Webhooks & Analytics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="events", db_index=True
    )
    event_type = models.CharField(
        max_length=50, choices=PaymentEventType.choices, db_index=True
    )
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = "payment_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} -> {self.payment.payment_id}"
