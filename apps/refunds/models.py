import uuid

from common.models import SoftDeleteModel, TimeStampedModel
from customer.models import CustomerProfile
from django.db import models
from merchant.models import MerchantProfile
from orders.models import Order
from payments.models import Payment


class RefundStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class Refund(TimeStampedModel, SoftDeleteModel):
    """
    Refund Entity representing partial or full reimbursement of a captured payment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refund_id = models.CharField(
        max_length=100, unique=True, db_index=True
    )  # rfnd_xxxx
    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="refunds", db_index=True
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="refunds", db_index=True
    )
    merchant = models.ForeignKey(
        MerchantProfile, on_delete=models.CASCADE, related_name="refunds", db_index=True
    )
    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        related_name="refunds",
        null=True,
        blank=True,
        db_index=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    currency = models.CharField(max_length=3, default="INR", db_index=True)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.CREATED,
        db_index=True,
    )
    failure_code = models.CharField(max_length=50, blank=True)
    failure_reason = models.TextField(blank=True)
    gateway_refund_id = models.CharField(max_length=100, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    requested_by = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "refunds"
        verbose_name = "Refund"
        verbose_name_plural = "Refunds"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "status", "created_at"]),
            models.Index(fields=["payment", "status"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["gateway_refund_id"]),
        ]

    def __str__(self):
        return f"{self.refund_id} - {self.amount} {self.currency} [{self.status}]"


class RefundLedgerAction(models.TextChoices):
    REFUND_CREATED = "REFUND_CREATED", "Refund Created"
    REFUND_PROCESSING = "REFUND_PROCESSING", "Refund Processing"
    REFUND_SUCCESS = "REFUND_SUCCESS", "Refund Success"
    REFUND_FAILED = "REFUND_FAILED", "Refund Failed"


class RefundLedger(models.Model):
    """
    Immutable Financial Audit Ledger for every Refund action.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refund = models.ForeignKey(
        Refund, on_delete=models.CASCADE, related_name="ledger_entries", db_index=True
    )
    action = models.CharField(
        max_length=50, choices=RefundLedgerAction.choices, db_index=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=RefundStatus.choices)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "refund_ledger"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} -> {self.refund.refund_id} ({self.status})"


class RefundEventType(models.TextChoices):
    CREATED = "refund.created", "Refund Created"
    PROCESSING = "refund.processing", "Refund Processing"
    SUCCEEDED = "refund.succeeded", "Refund Succeeded"
    FAILED = "refund.failed", "Refund Failed"


class RefundEvent(TimeStampedModel):
    """
    Domain Event Log tracking refund status lifecycle for Webhooks & Analytics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refund = models.ForeignKey(
        Refund, on_delete=models.CASCADE, related_name="events", db_index=True
    )
    event_type = models.CharField(
        max_length=50, choices=RefundEventType.choices, db_index=True
    )
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = "refund_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} -> {self.refund.refund_id}"


class DeadLetterRefundTask(TimeStampedModel):
    """
    Dead Letter Queue (DLQ) model storing permanently failed refund tasks for operator review.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refund = models.ForeignKey(
        Refund, on_delete=models.CASCADE, related_name="dlq_records"
    )
    error_message = models.TextField()
    retry_count = models.IntegerField(default=0)
    resolved = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "refund_dead_letter_queue"
        ordering = ["-created_at"]

    def __str__(self):
        return f"DLQ: {self.refund.refund_id} - Resolved: {self.resolved}"
