import pytest
from common.response import APIResponse
from common.utils import generate_hmac_signature, generate_unique_id, hash_secret
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestHealthCheckView:
    def test_health_check_endpoint(self, api_client):
        url = reverse("health-check")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]
        data = response.json()
        assert "success" in data
        assert "correlation_id" in data
        assert "services" in data["data"]


class TestCommonUtilities:
    def test_generate_unique_id(self):
        order_id = generate_unique_id("ord", length=16)
        assert order_id.startswith("ord_")
        assert len(order_id) == 20  # 4 + 16

    def test_hash_secret(self):
        raw = "sk_live_12345"
        hashed = hash_secret(raw)
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex string length

    def test_hmac_signature(self):
        payload = '{"event": "payment.captured"}'
        secret = "whsec_test_12345"
        sig = generate_hmac_signature(payload, secret)
        assert isinstance(sig, str)
        assert len(sig) == 64


class TestAPIResponseBuilder:
    def test_success_response(self):
        res = APIResponse.success(data={"foo": "bar"}, message="OK")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["success"] is True
        assert res.data["data"] == {"foo": "bar"}

    def test_error_response(self):
        res = APIResponse.error(
            message="Failed", code="TEST_ERR", status_code=status.HTTP_400_BAD_REQUEST
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data["success"] is False
        assert res.data["error"]["code"] == "TEST_ERR"
