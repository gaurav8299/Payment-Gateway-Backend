import logging
from typing import Any, Dict

from common.utils import generate_unique_id
from merchant.models import MerchantProfile
from webhooks.models import OutboxEvent

logger = logging.getLogger("payment_gateway")


class EventPublisher:
    """
    Centralized Event Publisher implementing Transactional Outbox Pattern.
    Saves OutboxEvent within local database transaction to guarantee reliable event dispatch.
    """

    @classmethod
    def publish(
        cls,
        event_type: str,
        resource_type: str,
        resource_id: str,
        payload: Dict[str, Any],
        merchant: MerchantProfile,
    ) -> OutboxEvent:
        event_id = generate_unique_id("evt", length=24)

        outbox_entry = OutboxEvent.objects.create(
            event_id=event_id,
            merchant=merchant,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
            processed=False,
        )

        logger.info(
            f"Published event '{event_type}' to Transactional Outbox ({event_id})."
        )

        # Dispatch async Celery outbox worker task safely
        try:
            from webhooks.tasks import process_outbox_events_task

            process_outbox_events_task.delay()
        except Exception as e:
            logger.warning(f"Failed to dispatch outbox task via Celery broker: {e}")

        return outbox_entry
