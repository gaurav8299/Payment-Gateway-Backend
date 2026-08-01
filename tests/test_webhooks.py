import time

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from django.urls import reverse
from merchant.services.merchant_service import MerchantService
from rest_framework import status
from webhooks.publisher import EventPublisher
from webhooks.security import generate_webhook_signature, verify_webhook_signature


@pytest.mark.django_db
class TestHMACSignatureAndReplayProtection:
    def test_hmac_signature_generation_and_verification(self):
        payload = '{"event": "payment.captured", "amount": 1000}'
        secret = "whsec_test_secret_key_12345"

        sig_header, ts = generate_webhook_signature(payload, secret)
        assert sig_header.startswith("t=")
        assert "v1=" in sig_header

        # Verify signature
        is_valid = verify_webhook_signature(
            payload, sig_header, secret, tolerance_seconds=300
        )
        assert is_valid is True

    def test_replay_protection_rejects_expired_timestamp(self):
        payload = '{"event": "payment.captured"}'
        secret = "whsec_test_secret_key_12345"

        # Create timestamp older than 5 minutes (360 seconds ago)
        old_timestamp = int(time.time()) - 360
        sig_header, _ = generate_webhook_signature(
            payload, secret, timestamp=old_timestamp
        )

        # Verification must reject payload due to timestamp expiration!
        is_valid = verify_webhook_signature(
            payload, sig_header, secret, tolerance_seconds=300
        )
        assert is_valid is False


@pytest.mark.django_db
class TestTransactionalOutboxAndEventPublisher:
    def test_event_publisher_inserts_outbox_event(self):
        merchant_user = UserRepository.create_user(
            email="pub_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)

        outbox = EventPublisher.publish(
            event_type="payment.captured",
            resource_type="payment",
            resource_id="pay_1234567890",
            payload={"amount": 500.00},
            merchant=merchant,
        )
        assert outbox.id is not None
        assert outbox.event_type == "payment.captured"

        # Celery eager task processes outbox entry immediately upon publish
        outbox.refresh_from_db()
        assert outbox.processed is True


@pytest.mark.django_db
class TestWebhookAPIEndpoints:
    def test_webhook_endpoint_crud_and_secret_rotation(self, api_client):
        UserRepository.create_user(
            email="wh_api_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        _, tokens = AuthService.login_user("wh_api_m@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Create Webhook Endpoint
        create_url = reverse("webhooks:endpoint_list_create")
        payload = {
            "name": "Primary Webhook Receiver",
            "url": "https://api.merchant.com/webhooks/",
            "enabled_events": ["payment.captured", "refund.succeeded"],
            "description": "Production Payment Notifications",
        }
        res = api_client.post(create_url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        endpoint_id = res.json()["data"]["endpoint_id"]
        secret_key = res.json()["data"]["secret_key"]
        assert secret_key.startswith("whsec_")

        # Rotate Secret API
        rotate_url = reverse(
            "webhooks:endpoint_rotate_secret", kwargs={"endpoint_id": endpoint_id}
        )
        r_res = api_client.post(rotate_url)
        assert r_res.status_code == status.HTTP_200_OK
        new_secret = r_res.json()["data"]["new_secret_key"]
        assert new_secret != secret_key

        # Send Test Ping API
        test_url = reverse(
            "webhooks:endpoint_test_ping", kwargs={"endpoint_id": endpoint_id}
        )
        t_res = api_client.post(test_url)
        assert t_res.status_code == status.HTTP_200_OK
        assert t_res.json()["data"]["event_type"] == "ping"
