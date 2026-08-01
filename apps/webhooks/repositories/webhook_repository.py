from typing import List, Optional, Tuple
from uuid import UUID

from common.utils import generate_unique_id, hash_secret
from django.db.models import QuerySet
from merchant.models import MerchantProfile
from webhooks.models import (
    EndpointStatus,
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEvent,
)


class WebhookRepository:
    """
    Repository class providing data access routines for Webhook infrastructure.
    """

    @staticmethod
    def create_endpoint(
        merchant: MerchantProfile,
        name: str,
        url: str,
        enabled_events: List[str],
        description: str = "",
        api_version: str = "v1",
    ) -> Tuple[WebhookEndpoint, str]:
        endpoint_id_str = generate_unique_id("we", length=24)
        raw_secret_key = generate_unique_id("whsec", length=32)
        hashed_secret = hash_secret(raw_secret_key)

        endpoint = WebhookEndpoint.objects.create(
            endpoint_id=endpoint_id_str,
            merchant=merchant,
            name=name,
            url=url,
            hashed_secret_key=hashed_secret,
            status=EndpointStatus.ACTIVE,
            enabled_events=enabled_events or ["*"],
            api_version=api_version,
            description=description,
        )
        return endpoint, raw_secret_key

    @staticmethod
    def get_endpoint_by_id(
        endpoint_id: UUID | str, merchant: Optional[MerchantProfile] = None
    ) -> Optional[WebhookEndpoint]:
        try:
            qs = WebhookEndpoint.objects.all()
            if merchant:
                qs = qs.filter(merchant=merchant)
            return qs.get(endpoint_id=endpoint_id)
        except WebhookEndpoint.DoesNotExist:
            try:
                qs = WebhookEndpoint.objects.all()
                if merchant:
                    qs = qs.filter(merchant=merchant)
                return qs.get(id=endpoint_id)
            except (WebhookEndpoint.DoesNotExist, ValueError):
                return None

    @staticmethod
    def rotate_secret(endpoint: WebhookEndpoint) -> str:
        new_raw_secret = generate_unique_id("whsec", length=32)
        endpoint.hashed_secret_key = hash_secret(new_raw_secret)
        endpoint.save(update_fields=["hashed_secret_key", "updated_at"])
        return new_raw_secret

    @staticmethod
    def list_endpoints(merchant: MerchantProfile) -> QuerySet:
        return WebhookEndpoint.objects.filter(merchant=merchant)

    @staticmethod
    def list_events(merchant: MerchantProfile) -> QuerySet:
        return WebhookEvent.objects.filter(merchant=merchant)

    @staticmethod
    def list_deliveries(merchant: MerchantProfile) -> QuerySet:
        return WebhookDelivery.objects.filter(endpoint__merchant=merchant)

    @staticmethod
    def get_delivery_by_id(
        delivery_id: str, merchant: MerchantProfile
    ) -> Optional[WebhookDelivery]:
        try:
            return WebhookDelivery.objects.get(
                delivery_id=delivery_id, endpoint__merchant=merchant
            )
        except WebhookDelivery.DoesNotExist:
            return None
