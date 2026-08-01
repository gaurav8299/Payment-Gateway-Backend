from common.utils import hash_secret
from django.utils import timezone
from merchant.models import MerchantAPIKey
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class MerchantAPIKeyAuthentication(BaseAuthentication):
    """
    Custom DRF Authentication backend validating Merchant Publishable & Secret API keys.
    Extracts key from `X-API-Key` or `Authorization: Bearer sk_live_...` headers.
    """

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY")
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        if not api_key and auth_header and auth_header.startswith("Bearer "):
            bearer_token = auth_header.split(" ")[1]
            if bearer_token.startswith("sk_live_") or bearer_token.startswith(
                "pk_live_"
            ):
                api_key = bearer_token

        if not api_key:
            return None  # Pass to next authentication backend (e.g. SimpleJWT)

        if api_key.startswith("pk_live_"):
            # Publishable Key match
            try:
                key_obj = MerchantAPIKey.objects.select_related(
                    "merchant", "merchant__user"
                ).get(publishable_key=api_key, is_active=True)
            except MerchantAPIKey.DoesNotExist:
                raise AuthenticationFailed("Invalid or inactive Publishable API Key.")
        elif api_key.startswith("sk_live_"):
            # Secret Key match (hashed in DB)
            hashed_key = hash_secret(api_key)
            try:
                key_obj = MerchantAPIKey.objects.select_related(
                    "merchant", "merchant__user"
                ).get(hashed_secret_key=hashed_key, is_active=True)
            except MerchantAPIKey.DoesNotExist:
                raise AuthenticationFailed("Invalid or inactive Secret API Key.")
        else:
            raise AuthenticationFailed("Invalid API Key format.")

        # Expiration check
        if key_obj.expires_at and key_obj.expires_at < timezone.now():
            raise AuthenticationFailed("API Key has expired.")

        # Update last used timestamp
        key_obj.last_used_at = timezone.now()
        key_obj.save(update_fields=["last_used_at"])

        # Attach merchant to request context
        request.merchant = key_obj.merchant
        return (key_obj.merchant.user, key_obj)
