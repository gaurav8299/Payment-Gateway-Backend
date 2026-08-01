import logging
from typing import Any, Dict

from common.utils import generate_unique_id
from notifications.models import Notification, NotificationChannel, NotificationStatus
from notifications.tasks import send_notification_task

logger = logging.getLogger("payment_gateway")


class DomainEventSubscriber:
    """
    Subscribes to domain events published to Transactional Outbox and dispatches async notifications.
    """

    @classmethod
    def handle_event(
        cls, event_type: str, payload: Dict[str, Any], recipient_email: str
    ):
        if not recipient_email:
            return

        subject_map = {
            "payment.captured": "Payment Receipt - Payment Successful",
            "refund.succeeded": "Refund Processed Successfully",
            "order.cancelled": "Order Cancelled Notification",
            "merchant.created": "Welcome to Payment Gateway Platform",
        }

        subject = subject_map.get(event_type, f"Event Notification: {event_type}")
        notif_id = generate_unique_id("notif", length=24)

        notification = Notification.objects.create(
            notification_id=notif_id,
            recipient=recipient_email,
            recipient_type="CUSTOMER",
            channel=NotificationChannel.EMAIL,
            subject=subject,
            template_name=f"templates/{event_type}.html",
            payload={
                "event_type": event_type,
                "details": payload,
                "message": f"Details for {event_type}: {payload}",
            },
            status=NotificationStatus.PENDING,
        )

        send_notification_task.delay(notification.notification_id)
        logger.info(
            f"Subscribed event '{event_type}' dispatched notification '{notif_id}'."
        )
