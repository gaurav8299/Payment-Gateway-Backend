import uuid

from common.models import TimeStampedModel
from django.db import models


class NotificationChannel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    IN_APP = "IN_APP", "In-App"
    SMS = "SMS", "SMS"
    PUSH = "PUSH", "Push Notification"
    WEBHOOK = "WEBHOOK", "Webhook"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class Notification(TimeStampedModel):
    """
    Notification Entity recording email, SMS, and in-app message dispatches.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_id = models.CharField(
        max_length=100, unique=True, db_index=True
    )  # notif_xxxx
    recipient = models.CharField(
        max_length=255, db_index=True
    )  # Email address or phone
    recipient_type = models.CharField(max_length=20, default="CUSTOMER", db_index=True)
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL,
        db_index=True,
    )
    subject = models.CharField(max_length=255)
    template_name = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    retry_count = models.IntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "status"]),
            models.Index(fields=["channel", "status"]),
        ]

    def __str__(self):
        return f"{self.notification_id} -> {self.recipient} [{self.status}]"
