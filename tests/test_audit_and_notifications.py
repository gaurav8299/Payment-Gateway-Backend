import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from audit_logs.models import AuditLog
from audit_logs.sanitizer import sanitize_payload
from audit_logs.services.audit_service import AuditService
from django.urls import reverse
from notifications.models import Notification, NotificationStatus
from notifications.subscribers import DomainEventSubscriber
from rest_framework import status


@pytest.mark.django_db
class TestSanitizerAndAuditBackends:
    def test_sanitizer_masks_sensitive_keys(self):
        raw_payload = {
            "email": "user@example.com",
            "password": "SecretPassword123!",
            "card_number": "4242424242424242",
            "secret_key": "whsec_super_secret_123",
            "nested": {
                "otp": "123456",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            },
        }

        sanitized = sanitize_payload(raw_payload)
        assert sanitized["email"] == "user@example.com"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["card_number"] == "[REDACTED]"
        assert sanitized["secret_key"] == "[REDACTED]"
        assert sanitized["nested"]["otp"] == "[REDACTED]"
        assert sanitized["nested"]["token"] == "[REDACTED]"

    def test_database_and_service_audit_backend(self):
        AuditService.log(
            {
                "event_type": "payment.captured",
                "actor_type": "MERCHANT",
                "actor_id": "m_12345",
                "resource_type": "payment",
                "resource_id": "pay_54321",
                "action": "PAYMENT_CAPTURED",
                "request_payload": {"password": "ShouldBeRedacted"},
            }
        )

        audit_entry = AuditLog.objects.filter(resource_id="pay_54321").first()
        assert audit_entry is not None
        assert audit_entry.request_payload["password"] == "[REDACTED]"


@pytest.mark.django_db
class TestNotificationSystemAndEventSubscribers:
    def test_domain_event_subscriber_creates_notification(self):
        DomainEventSubscriber.handle_event(
            event_type="payment.captured",
            payload={"payment_id": "pay_9999", "amount": "1500.00"},
            recipient_email="customer@example.com",
        )

        notif = Notification.objects.filter(recipient="customer@example.com").first()
        assert notif is not None
        assert (
            notif.status == NotificationStatus.SENT
        )  # Celery eager task sends email immediately!
        assert "Payment Receipt" in notif.subject


@pytest.mark.django_db
class TestAuditLogAndNotificationAPIs:
    def test_audit_logs_and_notifications_apis(self, api_client):
        UserRepository.create_user(
            email="admin_audit@example.com",
            password="Password123!",
            role=UserRole.ADMIN,
        )
        _, tokens = AuthService.login_user("admin_audit@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Get Audit Logs API
        audit_url = reverse("audit_logs:audit_log_list")
        a_res = api_client.get(audit_url)
        assert a_res.status_code == status.HTTP_200_OK

        # Get Notifications API
        notif_url = reverse("notifications:notification_list")
        n_res = api_client.get(notif_url)
        assert n_res.status_code == status.HTTP_200_OK
