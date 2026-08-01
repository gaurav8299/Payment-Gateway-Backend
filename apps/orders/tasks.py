import logging

from celery import shared_task
from django.utils import timezone
from orders.models import Order, OrderEvent, OrderEventType, OrderStatus

logger = logging.getLogger("payment_gateway")


@shared_task
def auto_expire_pending_orders_task():
    """
    Celery task periodically executed by Celery Beat to automatically transition
    expired PENDING orders to EXPIRED state.
    """
    now = timezone.now()
    expired_orders = Order.objects.filter(
        status=OrderStatus.PENDING,
        expires_at__isnull=False,
        expires_at__lte=now,
    )

    count = 0
    for order in expired_orders:
        order.status = OrderStatus.EXPIRED
        order.save(update_fields=["status", "updated_at"])

        # Record domain event
        OrderEvent.objects.create(
            order=order,
            event_type=OrderEventType.EXPIRED,
            payload={
                "order_number": order.order_number,
                "amount": str(order.amount),
                "currency": order.currency,
                "expired_at": now.isoformat(),
            },
        )
        count += 1

    if count > 0:
        logger.info(f"Auto-expired {count} pending orders successfully.")
    return count
