import json
import logging
import time
import urllib.error
import urllib.request

from celery import shared_task
from common.utils import generate_unique_id
from django.utils import timezone
from webhooks.models import (
    DeliveryStatus,
    EndpointStatus,
    OutboxEvent,
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEvent,
    WebhookEventStatus,
)
from webhooks.security import generate_webhook_signature

logger = logging.getLogger("payment_gateway")


@shared_task
def process_outbox_events_task():
    """
    Asynchronous Outbox Worker querying unprocessed OutboxEvent entries
    and fanning out delivery tasks to matching merchant endpoints.
    """
    unprocessed_events = OutboxEvent.objects.filter(processed=False).order_by(
        "created_at"
    )[:100]

    for outbox in unprocessed_events:
        # Create WebhookEvent log
        webhook_event, _ = WebhookEvent.objects.get_or_create(
            event_id=outbox.event_id,
            defaults={
                "merchant": outbox.merchant,
                "event_type": outbox.event_type,
                "resource_type": outbox.resource_type,
                "resource_id": outbox.resource_id,
                "payload": outbox.payload,
                "status": WebhookEventStatus.PENDING,
            },
        )

        # Match active endpoints for merchant subscribed to this event_type
        endpoints = WebhookEndpoint.objects.filter(
            merchant=outbox.merchant, status=EndpointStatus.ACTIVE
        )

        matching_endpoints = [
            ep
            for ep in endpoints
            if "*" in ep.enabled_events or outbox.event_type in ep.enabled_events
        ]

        for ep in matching_endpoints:
            delivery_id = generate_unique_id("del", length=24)
            delivery = WebhookDelivery.objects.create(
                delivery_id=delivery_id,
                event=webhook_event,
                endpoint=ep,
                attempt_number=1,
                status=DeliveryStatus.PENDING,
            )
            # Dispatch async delivery task
            deliver_webhook_task.delay(delivery.delivery_id)

        # Mark Outbox entry as processed
        outbox.processed = True
        outbox.processed_at = timezone.now()
        outbox.save(update_fields=["processed", "processed_at"])

    return len(unprocessed_events)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def deliver_webhook_task(self, delivery_id_str: str):
    """
    Asynchronous task performing HTTP POST delivery to merchant webhook endpoint with HMAC signatures.
    Implements exponential backoff retries and Dead Letter Queue logging.
    """
    try:
        delivery = WebhookDelivery.objects.get(delivery_id=delivery_id_str)
    except WebhookDelivery.DoesNotExist:
        logger.error(f"WebhookDelivery '{delivery_id_str}' not found.")
        return False

    endpoint = delivery.endpoint
    event = delivery.event

    payload_data = {
        "id": event.event_id,
        "object": "event",
        "type": event.event_type,
        "created": int(event.created_at.timestamp()),
        "data": {"object": event.payload},
    }
    payload_json = json.dumps(payload_data)

    # Generate HMAC Signature Header (Use endpoint.hashed_secret_key as secret identifier for test)
    sig_header, ts = generate_webhook_signature(
        payload_json, endpoint.hashed_secret_key
    )

    headers = {
        "Content-Type": "application/json",
        "X-Gateway-Event": event.event_type,
        "X-Gateway-Timestamp": str(ts),
        "X-Gateway-Signature": sig_header,
        "User-Agent": "PaymentGateway-Webhook/1.0",
    }

    start_time = time.time()
    http_status = None
    response_text = ""
    success = False

    try:
        req = urllib.request.Request(
            url=endpoint.url,
            data=payload_json.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:  # nosec B310
            http_status = response.status
            response_text = response.read().decode("utf-8", errors="ignore")[:1000]
            if 200 <= http_status < 300:
                success = True
    except urllib.error.HTTPError as e:
        http_status = e.code
        response_text = e.read().decode("utf-8", errors="ignore")[:1000]
    except Exception as e:
        response_text = str(e)[:500]

    duration_ms = int((time.time() - start_time) * 1000)

    delivery.attempt_number = self.request.retries + 1
    delivery.http_status = http_status
    delivery.response_body = response_text
    delivery.duration_ms = duration_ms
    delivery.delivered_at = timezone.now()

    if success:
        delivery.status = DeliveryStatus.SUCCESS
        delivery.save()

        event.status = WebhookEventStatus.DELIVERED
        event.save(update_fields=["status"])

        endpoint.last_delivery_at = timezone.now()
        endpoint.last_success_at = timezone.now()
        endpoint.save(update_fields=["last_delivery_at", "last_success_at"])
        logger.info(
            f"Webhook delivery '{delivery_id_str}' to '{endpoint.url}' succeeded!"
        )
        return True
    else:
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = f"HTTP {http_status}: {response_text}"
        delivery.save()

        if self.request.retries >= self.max_retries:
            event.status = WebhookEventStatus.FAILED
            event.save(update_fields=["status"])
            logger.error(
                f"Webhook delivery '{delivery_id_str}' permanently failed after max retries."
            )
            return False

        # Retry with exponential backoff (1m, 5m, 15m...)
        backoff_delay = [60, 300, 900, 1800, 3600][min(self.request.retries, 4)]
        raise self.retry(countdown=backoff_delay)
