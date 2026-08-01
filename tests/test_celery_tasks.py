from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from analytics.tasks import generate_daily_summary_task
from celery.exceptions import Retry
from merchant.services.merchant_service import MerchantService
from notifications.models import Notification, NotificationChannel, NotificationStatus
from notifications.tasks import send_notification_task
from orders.repositories.order_repository import OrderRepository
from payments.models import PaymentMethod
from payments.repositories.payment_repository import PaymentRepository
from refunds.repositories.refund_repository import RefundRepository
from refunds.tasks import process_refund_task
from webhooks.models import (
    DeliveryStatus,
    OutboxEvent,
    WebhookDelivery,
    WebhookEvent,
    WebhookEventStatus,
)
from webhooks.repositories.webhook_repository import WebhookRepository
from webhooks.tasks import deliver_webhook_task, process_outbox_events_task


@pytest.mark.django_db
class TestCeleryTasksSuite:
    @patch("urllib.request.urlopen")
    def test_process_outbox_events_task(self, mock_urlopen):
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value.status = 200
        mock_cm.__enter__.return_value.read.return_value = b"OK"
        mock_urlopen.return_value = mock_cm

        merchant_user = UserRepository.create_user(
            email="celery_wh_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        WebhookRepository.create_endpoint(
            merchant=merchant,
            name="Celery Endpoint",
            url="https://example.com/webhook",
            enabled_events=["payment.captured"],
        )
        outbox = OutboxEvent.objects.create(
            event_id="evt_celery_1",
            merchant=merchant,
            event_type="payment.captured",
            resource_type="payment",
            resource_id="pay_outbox_1",
            payload={"amount": "100.00"},
            processed=False,
        )

        processed_count = process_outbox_events_task()
        assert processed_count >= 1

        outbox.refresh_from_db()
        assert outbox.processed is True

    @patch("urllib.request.urlopen")
    def test_deliver_webhook_task_failure_and_dead_letter(self, mock_urlopen):
        merchant_user = UserRepository.create_user(
            email="celery_fail_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        endpoint, _ = WebhookRepository.create_endpoint(
            merchant=merchant,
            name="Failing Endpoint",
            url="https://failing-endpoint.com/webhook",
            enabled_events=["payment.captured"],
        )
        event = WebhookEvent.objects.create(
            event_id="evt_fail_123",
            merchant=merchant,
            event_type="payment.captured",
            resource_type="payment",
            resource_id="pay_123",
            payload={"amount": "500.00"},
            status=WebhookEventStatus.PENDING,
        )
        delivery = WebhookDelivery.objects.create(
            delivery_id="del_fail_123",
            event=event,
            endpoint=endpoint,
            attempt_number=1,
            status=DeliveryStatus.PENDING,
        )

        mock_urlopen.side_effect = Exception("Connection Timeout")

        with pytest.raises(Retry):
            deliver_webhook_task(delivery.delivery_id)

        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.FAILED

    @patch("notifications.tasks.send_mail")
    def test_send_notification_task(self, mock_send_mail):
        mock_send_mail.return_value = 1
        notif = Notification.objects.create(
            notification_id="notif_celery_123",
            recipient="notif_task@example.com",
            subject="Celery Notification",
            template_name="welcome_email",
            channel=NotificationChannel.EMAIL,
        )

        res = send_notification_task("notif_celery_123")
        assert res is True

        notif.refresh_from_db()
        assert notif.status == NotificationStatus.SENT

    def test_process_refund_task_failure(self):
        merchant_user = UserRepository.create_user(
            email="refund_task_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        order = OrderRepository.create_order(
            order_number="ord_celery_ref",
            merchant=merchant,
            amount=Decimal("2000.00"),
            currency="INR",
        )
        payment = PaymentRepository.create_payment(
            payment_id_str="pay_celery_ref",
            order=order,
            merchant=merchant,
            amount=Decimal("2000.00"),
            currency="INR",
            payment_method=PaymentMethod.CARD,
            gateway="DUMMY",
        )
        refund = RefundRepository.create_refund(
            refund_id_str="rfnd_celery_fail",
            payment=payment,
            merchant=merchant,
            amount=Decimal("500.00"),
            currency="INR",
            reason="Defective item",
        )

        with patch(
            "payments.adapters.dummy_adapter.DummyGatewayAdapter.refund"
        ) as mock_ref:
            mock_ref.return_value = {
                "success": False,
                "message": "Gateway refund failure",
            }
            process_refund_task(refund.refund_id)

        refund.refresh_from_db()
        assert refund.status == "FAILED"

    def test_generate_daily_summary_task(self):
        generate_daily_summary_task()
