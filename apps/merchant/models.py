import uuid

from common.models import SoftDeleteModel, TimeStampedModel
from django.conf import settings
from django.db import models


class MerchantStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"


class BusinessType(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", "Individual"
    SOLE_PROPRIETORSHIP = "SOLE_PROPRIETORSHIP", "Sole Proprietorship"
    PARTNERSHIP = "PARTNERSHIP", "Partnership"
    PRIVATE_LIMITED = "PRIVATE_LIMITED", "Private Limited"
    PUBLIC_LIMITED = "PUBLIC_LIMITED", "Public Limited"
    LLP = "LLP", "Limited Liability Partnership"


class MerchantProfile(TimeStampedModel, SoftDeleteModel):
    """
    Merchant Profile Entity representing business organizations on the Payment Gateway.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_profile",
    )
    business_name = models.CharField(max_length=255, db_index=True)
    legal_business_name = models.CharField(max_length=255)
    business_type = models.CharField(
        max_length=50, choices=BusinessType.choices, default=BusinessType.INDIVIDUAL
    )
    merchant_category_code = models.CharField(max_length=10, default="5734")  # MCC
    gst_number = models.CharField(max_length=15, null=True, blank=True, db_index=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    website = models.URLField(null=True, blank=True)
    support_email = models.EmailField()
    support_phone = models.CharField(max_length=20)
    logo_url = models.URLField(null=True, blank=True)
    address = models.TextField()
    country = models.CharField(max_length=3, default="IN")
    currency = models.CharField(max_length=3, default="INR")
    timezone = models.CharField(max_length=50, default="UTC")
    status = models.CharField(
        max_length=20,
        choices=MerchantStatus.choices,
        default=MerchantStatus.PENDING,
        db_index=True,
    )

    class Meta:
        db_table = "merchant_profiles"
        verbose_name = "Merchant Profile"
        verbose_name_plural = "Merchant Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.business_name} ({self.status})"


class MerchantAPIKey(TimeStampedModel):
    """
    Merchant API Key pair (Publishable and Hashed Secret Keys).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        MerchantProfile, on_delete=models.CASCADE, related_name="api_keys"
    )
    name = models.CharField(max_length=100, default="Default Live Key")
    publishable_key = models.CharField(max_length=100, unique=True, db_index=True)
    hashed_secret_key = models.CharField(max_length=128, unique=True, db_index=True)
    secret_key_prefix = models.CharField(
        max_length=16
    )  # Store sk_live_XXXX for display
    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "merchant_api_keys"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.merchant.business_name}"


class MerchantWebhookSecret(TimeStampedModel):
    """
    Merchant Webhook HMAC Signing Secret.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.OneToOneField(
        MerchantProfile, on_delete=models.CASCADE, related_name="webhook_secret"
    )
    secret_prefix = models.CharField(max_length=16)
    hashed_secret = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "merchant_webhook_secrets"

    def __str__(self):
        return f"Webhook Secret - {self.merchant.business_name}"


class WebhookEventTypes(models.TextChoices):
    PAYMENT_CREATED = "payment.created", "Payment Created"
    PAYMENT_AUTHORIZED = "payment.authorized", "Payment Authorized"
    PAYMENT_CAPTURED = "payment.captured", "Payment Captured"
    PAYMENT_FAILED = "payment.failed", "Payment Failed"
    PAYMENT_REFUNDED = "payment.refunded", "Payment Refunded"
    REFUND_CREATED = "refund.created", "Refund Created"
    REFUND_COMPLETED = "refund.completed", "Refund Completed"


class WebhookEndpoint(TimeStampedModel):
    """
    Merchant Registered Webhook Callback URLs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.CASCADE,
        related_name="merchant_webhook_configs",
    )
    url = models.URLField()
    description = models.CharField(max_length=255, blank=True)
    enabled_events = models.JSONField(default=list)  # List of WebhookEventTypes
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "merchant_webhook_endpoints"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.url} ({self.merchant.business_name})"
