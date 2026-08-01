from typing import Any, Dict, Tuple

from accounts.models import User
from common.exceptions import BusinessLogicError, ResourceNotFoundError
from common.utils import generate_unique_id
from merchant.services.merchant_service import MerchantService
from webhooks.models import DeliveryStatus, WebhookDelivery, WebhookEndpoint
from webhooks.publisher import EventPublisher
from webhooks.repositories.webhook_repository import WebhookRepository
from webhooks.tasks import deliver_webhook_task


class WebhookService:
    """
    Service layer providing Webhook Endpoint management, Secret Rotation, Event Replay, and Testing.
    """

    @classmethod
    def create_endpoint(
        cls, user: User, validated_data: Dict[str, Any]
    ) -> Tuple[WebhookEndpoint, str]:
        merchant = MerchantService.get_or_create_profile(user)
        url = validated_data["url"]

        if not (
            url.startswith("https://")
            or url.startswith("http://localhost")
            or url.startswith("http://127.0.0.1")
        ):
            raise BusinessLogicError(
                detail="Webhook URL must use secure HTTPS protocol.",
                code="INVALID_WEBHOOK_URL",
            )

        endpoint, raw_secret = WebhookRepository.create_endpoint(
            merchant=merchant,
            name=validated_data["name"],
            url=url,
            enabled_events=validated_data.get("enabled_events", ["*"]),
            description=validated_data.get("description", ""),
            api_version=validated_data.get("api_version", "v1"),
        )
        return endpoint, raw_secret

    @classmethod
    def get_endpoint(cls, user: User, endpoint_id: str) -> WebhookEndpoint:
        merchant = MerchantService.get_or_create_profile(user)
        endpoint = WebhookRepository.get_endpoint_by_id(endpoint_id, merchant)
        if not endpoint:
            raise ResourceNotFoundError(detail="Webhook endpoint not found.")
        return endpoint

    @classmethod
    def rotate_secret(cls, user: User, endpoint_id: str) -> str:
        endpoint = cls.get_endpoint(user, endpoint_id)
        return WebhookRepository.rotate_secret(endpoint)

    @classmethod
    def replay_delivery(cls, user: User, delivery_id: str) -> WebhookDelivery:
        merchant = MerchantService.get_or_create_profile(user)
        orig_delivery = WebhookRepository.get_delivery_by_id(delivery_id, merchant)
        if not orig_delivery:
            raise ResourceNotFoundError(detail="Webhook delivery log not found.")

        new_delivery_id = generate_unique_id("del", length=24)
        new_delivery = WebhookDelivery.objects.create(
            delivery_id=new_delivery_id,
            event=orig_delivery.event,
            endpoint=orig_delivery.endpoint,
            attempt_number=orig_delivery.attempt_number + 1,
            status=DeliveryStatus.PENDING,
        )

        deliver_webhook_task.delay(new_delivery.delivery_id)
        return new_delivery

    @classmethod
    def send_test_event(
        cls, user: User, endpoint_id: str, event_type: str = "ping"
    ) -> Dict[str, Any]:
        endpoint = cls.get_endpoint(user, endpoint_id)
        merchant = endpoint.merchant

        payload = {
            "message": "Webhook endpoint test ping event",
            "endpoint_id": endpoint.endpoint_id,
        }

        outbox_entry = EventPublisher.publish(
            event_type=event_type,
            resource_type="test",
            resource_id=endpoint.endpoint_id,
            payload=payload,
            merchant=merchant,
        )

        return {
            "success": True,
            "event_id": outbox_entry.event_id,
            "event_type": event_type,
            "message": "Test webhook ping event published to transactional outbox.",
        }
