import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from common.exceptions import ResourceNotFoundError
from customer.services.customer_service import CustomerService
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestCustomerServiceAndIsolation:
    def test_customer_crud(self):
        user = UserRepository.create_user(
            email="cust_merchant@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        cust_data = {
            "name": "Bob Smith",
            "email": "bob@example.com",
            "phone": "+919876543210",
        }
        customer = CustomerService.create_customer(user, cust_data)

        assert customer.id is not None
        assert customer.name == "Bob Smith"
        assert customer.email == "bob@example.com"

        fetched = CustomerService.get_customer(user, str(customer.id))
        assert fetched.id == customer.id

    def test_merchant_isolation(self):
        merchant_a = UserRepository.create_user(
            email="merchant_a@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant_b = UserRepository.create_user(
            email="merchant_b@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )

        customer_a = CustomerService.create_customer(
            merchant_a, {"name": "Client A", "email": "clienta@example.com"}
        )

        # Merchant B attempts to fetch Merchant A's customer -> Must raise ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError):
            CustomerService.get_customer(merchant_b, str(customer_a.id))


@pytest.mark.django_db
class TestCustomerAPIEndpoints:
    def test_customer_api_create_and_list(self, api_client):
        UserRepository.create_user(
            email="cust_api@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        _, tokens = AuthService.login_user("cust_api@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        url = reverse("customer:customer_list_create")
        payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+919999988888",
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert "id" in res.json()["data"]

        # List customers
        list_res = api_client.get(url)
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.json()["data"]) == 1

    def test_saved_payment_method_tokenization(self, api_client):
        user = UserRepository.create_user(
            email="pm_merchant@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        customer = CustomerService.create_customer(
            user, {"name": "Token User", "email": "token@example.com"}
        )

        _, tokens = AuthService.login_user("pm_merchant@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        url = reverse(
            "customer:customer_payment_methods",
            kwargs={"customer_id": str(customer.id)},
        )
        payload = {
            "type": "CARD",
            "raw_card_number": "4242424242424242",
            "card_brand": "VISA",
            "exp_month": 11,
            "exp_year": 2028,
            "is_default": True,
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        pm_data = res.json()["data"]

        assert pm_data["card_token"].startswith("card_token_")
        assert pm_data["masked_card_number"] == "4242 **** **** 4242"
        # Ensure raw card number is NOT present in returned response!
        assert "raw_card_number" not in pm_data
