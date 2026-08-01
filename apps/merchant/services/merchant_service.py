from typing import Any, Dict, List, Tuple

from accounts.models import User
from common.exceptions import ResourceNotFoundError
from common.utils import generate_unique_id, hash_secret
from merchant.models import (
    MerchantAPIKey,
    MerchantProfile,
    MerchantStatus,
    WebhookEndpoint,
)
from merchant.repositories.merchant_repository import MerchantRepository


class MerchantService:
    """
    Business logic layer for Merchant Profiles, Key management, and Webhooks.
    """

    @classmethod
    def get_or_create_profile(cls, user: User) -> MerchantProfile:
        merchant = MerchantRepository.get_by_user(user)
        if not merchant:
            merchant = MerchantRepository.create_merchant_profile(
                user=user,
                business_name=f"{user.first_name or 'My'} Business",
                legal_business_name=f"{user.first_name or 'My'} Business Legal Entity",
                support_email=user.email,
                support_phone=user.phone_number or "+910000000000",
                address="Default Business Address",
                status=MerchantStatus.ACTIVE,
            )
        return merchant

    @classmethod
    def update_profile(
        cls, user: User, validated_data: Dict[str, Any]
    ) -> MerchantProfile:
        merchant = cls.get_or_create_profile(user)
        updated_merchant = MerchantRepository.update_merchant_profile(
            merchant, **validated_data
        )
        return updated_merchant

    @classmethod
    def generate_api_key(
        cls, user: User, name: str = "Default Live Key"
    ) -> Tuple[MerchantAPIKey, str]:
        """
        Generates Publishable Key (`pk_live_...`) and Secret Key (`sk_live_...`).
        Secret key is hashed via SHA-256 before storing. Raw secret key is returned ONCE.
        """
        merchant = cls.get_or_create_profile(user)

        publishable_key = generate_unique_id("pk_live", length=24)
        raw_secret_key = generate_unique_id("sk_live", length=32)
        hashed_secret_key = hash_secret(raw_secret_key)
        secret_prefix = f"{raw_secret_key[:12]}..."

        key_obj = MerchantRepository.create_api_key(
            merchant=merchant,
            name=name,
            publishable_key=publishable_key,
            hashed_secret_key=hashed_secret_key,
            secret_key_prefix=secret_prefix,
        )

        return key_obj, raw_secret_key

    @classmethod
    def list_api_keys(cls, user: User) -> List[MerchantAPIKey]:
        merchant = cls.get_or_create_profile(user)
        return MerchantRepository.get_api_keys(merchant)

    @classmethod
    def revoke_api_key(cls, user: User, key_id: str) -> bool:
        merchant = cls.get_or_create_profile(user)
        success = MerchantRepository.revoke_api_key(key_id, merchant)
        if not success:
            raise ResourceNotFoundError(detail="API key not found or already revoked.")
        return True

    @classmethod
    def rotate_webhook_secret(cls, user: User) -> str:
        """
        Generates/Rotates Webhook Secret (`whsec_...`).
        Stores hashed secret in DB and returns raw secret key ONCE.
        """
        merchant = cls.get_or_create_profile(user)
        raw_webhook_secret = generate_unique_id("whsec", length=32)
        hashed_secret = hash_secret(raw_webhook_secret)
        secret_prefix = f"{raw_webhook_secret[:10]}..."

        MerchantRepository.create_or_update_webhook_secret(
            merchant=merchant,
            secret_prefix=secret_prefix,
            hashed_secret=hashed_secret,
        )

        return raw_webhook_secret

    @classmethod
    def create_webhook_endpoint(
        cls, user: User, url: str, enabled_events: list, description: str = ""
    ) -> WebhookEndpoint:
        merchant = cls.get_or_create_profile(user)
        return MerchantRepository.create_webhook_endpoint(
            merchant=merchant,
            url=url,
            enabled_events=enabled_events,
            description=description,
        )

    @classmethod
    def list_webhook_endpoints(cls, user: User) -> List[WebhookEndpoint]:
        merchant = cls.get_or_create_profile(user)
        return MerchantRepository.list_webhook_endpoints(merchant)

    @classmethod
    def update_webhook_endpoint(
        cls, user: User, endpoint_id: str, data: dict
    ) -> WebhookEndpoint:
        merchant = cls.get_or_create_profile(user)
        endpoint = MerchantRepository.update_webhook_endpoint(
            endpoint_id, merchant, **data
        )
        if not endpoint:
            raise ResourceNotFoundError(detail="Webhook endpoint not found.")
        return endpoint

    @classmethod
    def delete_webhook_endpoint(cls, user: User, endpoint_id: str) -> bool:
        merchant = cls.get_or_create_profile(user)
        success = MerchantRepository.delete_webhook_endpoint(endpoint_id, merchant)
        if not success:
            raise ResourceNotFoundError(detail="Webhook endpoint not found.")
        return True

    @classmethod
    def get_merchant_stats(cls, user: User) -> Dict[str, Any]:
        merchant = cls.get_or_create_profile(user)
        return {
            "merchant_id": str(merchant.id),
            "business_name": merchant.business_name,
            "status": merchant.status,
            "currency": merchant.currency,
            "summary": {
                "total_revenue": 0.00,
                "total_payments_count": 0,
                "successful_payments_count": 0,
                "total_refunds_count": 0,
                "total_refunded_amount": 0.00,
            },
        }
