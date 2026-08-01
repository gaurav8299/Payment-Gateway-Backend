import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from notifications.models import Notification, NotificationStatus

logger = logging.getLogger("payment_gateway")


@shared_task(
    bind=True, queue="notification_queue", max_retries=3, default_retry_delay=10
)
def send_notification_task(self, notification_id_str: str):
    """
    Asynchronous Celery task rendering email templates and sending email notifications with retries.
    """
    try:
        notification = Notification.objects.get(notification_id=notification_id_str)
    except Notification.DoesNotExist:
        logger.error(f"Notification '{notification_id_str}' not found.")
        return False

    if notification.status == NotificationStatus.SENT:
        return True

    try:
        # Render plain-text fallback content from template payload
        payload = notification.payload or {}
        message_body = payload.get(
            "message", f"Notification for {notification.subject}"
        )

        # Send Email
        send_mail(
            subject=notification.subject,
            message=message_body,
            from_email=getattr(
                settings, "DEFAULT_FROM_EMAIL", "noreply@paymentgateway.com"
            ),
            recipient_list=[notification.recipient],
            fail_silently=False,
        )

        notification.status = NotificationStatus.SENT
        notification.sent_at = timezone.now()
        notification.save(update_fields=["status", "sent_at", "updated_at"])

        logger.info(
            f"Notification '{notification_id_str}' sent to '{notification.recipient}' successfully!"
        )
        return True

    except Exception as exc:
        logger.error(f"Failed to send notification '{notification_id_str}': {exc}")
        notification.retry_count = self.request.retries + 1
        notification.failure_reason = str(exc)

        if self.request.retries >= self.max_retries:
            notification.status = NotificationStatus.FAILED
            notification.save(
                update_fields=["status", "retry_count", "failure_reason", "updated_at"]
            )
            logger.error(
                f"Notification '{notification_id_str}' permanently failed after max retries."
            )
            return False

        notification.save(update_fields=["retry_count", "failure_reason", "updated_at"])
        raise self.retry(exc=exc, countdown=2**self.request.retries * 5)
