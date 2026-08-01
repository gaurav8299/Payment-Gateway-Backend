from typing import List, Optional
from uuid import UUID

from accounts.models import User
from merchant.models import (
    MerchantAPIKey,
    MerchantProfile,
    MerchantWebhookSecret,
    WebhookEndpoint,
)


class MerchantRepository:
    """
    Repository providing database operations for Merchant Profiles, API Keys, and Webhook management.
    """

    @staticmethod
    def get_by_id(merchant_id: UUID | str) -> Optional[MerchantProfile]:
        try:
            return MerchantProfile.objects.get(id=merchant_id)
        except MerchantProfile.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user: User) -> Optional[MerchantProfile]:
        try:
            return MerchantProfile.objects.get(user=user)
        except MerchantProfile.DoesNotExist:
            return None

    @staticmethod
    def create_merchant_profile(user: User, **kwargs) -> MerchantProfile:
        return MerchantProfile.objects.create(user=user, **kwargs)

    @staticmethod
    def update_merchant_profile(merchant: MerchantProfile, **kwargs) -> MerchantProfile:
        for attr, value in kwargs.items():
            if hasattr(merchant, attr) and value is not None:
                setattr(merchant, attr, value)
        merchant.save()
        return merchant

    @staticmethod
    def create_api_key(
        merchant: MerchantProfile,
        name: str,
        publishable_key: str,
        hashed_secret_key: str,
        secret_key_prefix: str,
        expires_at=None,
    ) -> MerchantAPIKey:
        return MerchantAPIKey.objects.create(
            merchant=merchant,
            name=name,
            publishable_key=publishable_key,
            hashed_secret_key=hashed_secret_key,
            secret_key_prefix=secret_key_prefix,
            expires_at=expires_at,
        )

    @staticmethod
    def get_api_keys(merchant: MerchantProfile) -> List[MerchantAPIKey]:
        return list(MerchantAPIKey.objects.filter(merchant=merchant, is_active=True))

    @staticmethod
    def revoke_api_key(key_id: UUID | str, merchant: MerchantProfile) -> bool:
        updated = MerchantAPIKey.objects.filter(id=key_id, merchant=merchant).update(
            is_active=False
        )
        return updated > 0

    @staticmethod
    def get_webhook_secret(
        merchant: MerchantProfile,
    ) -> Optional[MerchantWebhookSecret]:
        try:
            return MerchantWebhookSecret.objects.get(merchant=merchant, is_active=True)
        except MerchantWebhookSecret.DoesNotExist:
            return None

    @staticmethod
    def create_or_update_webhook_secret(
        merchant: MerchantProfile, secret_prefix: str, hashed_secret: str
    ) -> MerchantWebhookSecret:
        obj, created = MerchantWebhookSecret.objects.update_or_create(
            merchant=merchant,
            defaults={
                "secret_prefix": secret_prefix,
                "hashed_secret": hashed_secret,
                "is_active": True,
            },
        )
        return obj

    @staticmethod
    def create_webhook_endpoint(
        merchant: MerchantProfile, url: str, enabled_events: list, description: str = ""
    ) -> WebhookEndpoint:
        return WebhookEndpoint.objects.create(
            merchant=merchant,
            url=url,
            enabled_events=enabled_events,
            description=description,
        )

    @staticmethod
    def update_webhook_endpoint(
        endpoint_id: UUID | str, merchant: MerchantProfile, **kwargs
    ) -> Optional[WebhookEndpoint]:
        try:
            endpoint = WebhookEndpoint.objects.get(id=endpoint_id, merchant=merchant)
            for attr, value in kwargs.items():
                if hasattr(endpoint, attr) and value is not None:
                    setattr(endpoint, attr, value)
            endpoint.save()
            return endpoint
        except WebhookEndpoint.DoesNotExist:
            return None

    @staticmethod
    def delete_webhook_endpoint(
        endpoint_id: UUID | str, merchant: MerchantProfile
    ) -> bool:
        deleted, _ = WebhookEndpoint.objects.filter(
            id=endpoint_id, merchant=merchant
        ).delete()
        return deleted > 0

    @staticmethod
    def list_webhook_endpoints(merchant: MerchantProfile) -> List[WebhookEndpoint]:
        return list(WebhookEndpoint.objects.filter(merchant=merchant, is_active=True))
