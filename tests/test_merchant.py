import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from common.utils import hash_secret
from django.urls import reverse
from merchant.repositories.merchant_repository import MerchantRepository
from merchant.services.merchant_service import MerchantService
from rest_framework import status


@pytest.mark.django_db
class TestMerchantRepositoryAndService:
    def test_get_or_create_merchant_profile(self):
        user = UserRepository.create_user(
            email="merchant_user@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(user)
        assert merchant.id is not None
        assert merchant.user == user
        assert merchant.support_email == "merchant_user@example.com"

    def test_generate_api_key_hashes_secret(self):
        user = UserRepository.create_user(
            email="key_user@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        key_obj, raw_secret = MerchantService.generate_api_key(user, "Production Key")

        assert raw_secret.startswith("sk_live_")
        assert key_obj.publishable_key.startswith("pk_live_")
        # Ensure secret key is hashed in DB
        assert key_obj.hashed_secret_key == hash_secret(raw_secret)
        assert key_obj.hashed_secret_key != raw_secret

    def test_rotate_webhook_secret(self):
        user = UserRepository.create_user(
            email="wh_user@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        raw_secret = MerchantService.rotate_webhook_secret(user)
        assert raw_secret.startswith("whsec_")

        merchant = MerchantService.get_or_create_profile(user)
        secret_obj = MerchantRepository.get_webhook_secret(merchant)
        assert secret_obj is not None
        assert secret_obj.hashed_secret == hash_secret(raw_secret)


@pytest.mark.django_db
class TestMerchantAPIEndpoints:
    def test_merchant_profile_get_and_patch(self, api_client):
        UserRepository.create_user(
            email="m_api@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        from accounts.services.auth_service import AuthService

        _, tokens = AuthService.login_user("m_api@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        url = reverse("merchant:merchant_profile")
        get_res = api_client.get(url)
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.json()["data"]["support_email"] == "m_api@example.com"

        patch_res = api_client.patch(
            url, {"business_name": "Updated Acme Corp"}, format="json"
        )
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.json()["data"]["business_name"] == "Updated Acme Corp"

    def test_generate_api_keys_endpoint(self, api_client):
        UserRepository.create_user(
            email="keygen@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        from accounts.services.auth_service import AuthService

        _, tokens = AuthService.login_user("keygen@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        url = reverse("merchant:api_key_list_create")
        res = api_client.post(url, {"name": "Test Key"}, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()["data"]
        assert "secret_key" in data
        assert data["secret_key"].startswith("sk_live_")
        assert data["publishable_key"].startswith("pk_live_")

    def test_webhook_endpoints_crud(self, api_client):
        UserRepository.create_user(
            email="whendpoints@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        from accounts.services.auth_service import AuthService

        _, tokens = AuthService.login_user("whendpoints@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        url = reverse("merchant:webhook_endpoint_list_create")
        payload = {
            "url": "https://example.com/webhooks/",
            "description": "Production Webhook Target",
            "enabled_events": ["payment.captured", "refund.created"],
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        endpoint_id = res.json()["data"]["id"]

        # List endpoints
        list_res = api_client.get(url)
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.json()["data"]) == 1

        # Delete endpoint
        del_url = reverse(
            "merchant:webhook_endpoint_detail", kwargs={"endpoint_id": endpoint_id}
        )
        del_res = api_client.delete(del_url)
        assert del_res.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestMerchantAPIKeyAuthentication:
    def test_authenticate_via_secret_key_header(self, api_client):
        user = UserRepository.create_user(
            email="keyauth@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        _, raw_secret = MerchantService.generate_api_key(user, "Auth Key")

        # Authenticate using X-API-Key header
        api_client.credentials(HTTP_X_API_KEY=raw_secret)
        url = reverse("merchant:merchant_profile")
        res = api_client.get(url)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["data"]["support_email"] == "keyauth@example.com"
