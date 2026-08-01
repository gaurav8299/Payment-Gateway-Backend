import uuid

from django.db import models


class AuditActorType(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    MERCHANT = "MERCHANT", "Merchant"
    CUSTOMER = "CUSTOMER", "Customer"
    SYSTEM = "SYSTEM", "System"


class AuditLog(models.Model):
    """
    Audit Log model storing sanitized, structured audit traces of all API requests & domain operations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit_id = models.CharField(max_length=100, unique=True, db_index=True)  # aud_xxxx
    event_type = models.CharField(max_length=100, db_index=True)
    actor_type = models.CharField(
        max_length=20, choices=AuditActorType.choices, default=AuditActorType.SYSTEM
    )
    actor_id = models.CharField(max_length=100, db_index=True, blank=True)
    resource_type = models.CharField(max_length=50, db_index=True)
    resource_id = models.CharField(max_length=100, db_index=True)
    http_method = models.CharField(max_length=10, blank=True)
    endpoint = models.CharField(max_length=255, blank=True)
    request_id = models.CharField(
        max_length=100, db_index=True, blank=True
    )  # Correlation ID
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=100)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["actor_type", "actor_id"]),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["request_id"]),
        ]

    def __str__(self):
        return f"{self.audit_id} [{self.action}] -> {self.resource_type}:{self.resource_id} ({self.created_at})"
