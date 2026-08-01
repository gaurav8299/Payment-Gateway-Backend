import uuid

from common.models import SoftDeleteModel, TimeStampedModel
from django.db import models
from merchant.models import MerchantProfile


class EndpointStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DISABLED = "DISABLED", "Disabled"


class WebhookEventStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    DELIVERED = "DELIVERED", "Delivered"
    FAILED = "FAILED", "Failed"


class DeliveryStatus(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    PENDING = "PENDING", "Pending"


class OutboxEvent(models.Model):
    """
    Transactional Outbox model ensuring atomic event insertion alongside business domain mutations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=100, unique=True, db_index=True)  # evt_xxxx
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="outbox_events",
        db_index=True,
    )
    event_type = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "transactional_outbox"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["processed", "created_at"]),
        ]

    def __str__(self):
        return (
            f"Outbox: {self.event_id} ({self.event_type}) - Processed: {self.processed}"
        )


class WebhookEndpoint(TimeStampedModel, SoftDeleteModel):
    """
    Merchant Webhook Receiver Endpoint destination configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint_id = models.CharField(
        max_length=100, unique=True, db_index=True
    )  # we_xxxx
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="webhook_endpoints",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    hashed_secret_key = models.CharField(max_length=255)  # SHA-256 hash of whsec_...
    status = models.CharField(
        max_length=20,
        choices=EndpointStatus.choices,
        default=EndpointStatus.ACTIVE,
        db_index=True,
    )
    enabled_events = models.JSONField(
        default=list
    )  # List of event types e.g. ["payment.captured"]
    api_version = models.CharField(max_length=20, default="v1")
    description = models.TextField(blank=True)
    last_delivery_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "webhook_endpoints"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.url}) [{self.status}]"


class WebhookEvent(TimeStampedModel):
    """
    Persistent log of generated domain events published for Webhook dispatches.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=100, unique=True, db_index=True)  # evt_xxxx
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="webhook_events",
        db_index=True,
    )
    event_type = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=WebhookEventStatus.choices,
        default=WebhookEventStatus.PENDING,
        db_index=True,
    )

    class Meta:
        db_table = "webhook_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "event_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_id} ({self.event_type}) [{self.status}]"


class WebhookDelivery(models.Model):
    """
    Audit log tracking individual Webhook delivery attempts to merchant HTTP endpoints.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery_id = models.CharField(
        max_length=100, unique=True, db_index=True
    )  # del_xxxx
    event = models.ForeignKey(
        WebhookEvent, on_delete=models.CASCADE, related_name="deliveries", db_index=True
    )
    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
        db_index=True,
    )
    http_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempt_number = models.IntegerField(default=1)
    duration_ms = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    delivered_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "webhook_deliveries"
        ordering = ["-delivered_at"]
        indexes = [
            models.Index(fields=["endpoint", "status", "delivered_at"]),
            models.Index(fields=["event", "status"]),
        ]

    def __str__(self):
        return f"Delivery {self.delivery_id} -> {self.endpoint.url} [{self.status}]"
