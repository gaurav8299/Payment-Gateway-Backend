from datetime import timedelta
from decimal import Decimal

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from common.exceptions import BusinessLogicError
from django.urls import reverse
from django.utils import timezone
from orders.models import OrderStatus
from orders.services.order_service import OrderService
from orders.state_machine import validate_order_status_transition
from orders.tasks import auto_expire_pending_orders_task
from rest_framework import status


@pytest.mark.django_db
class TestOrderDomainAndStateMachine:
    def test_create_order(self):
        merchant_user = UserRepository.create_user(
            email="ord_merchant@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        data = {
            "amount": "1500.50",
            "currency": "INR",
            "description": "Web Development Services",
        }
        order = OrderService.create_order(merchant_user, data)

        assert order.id is not None
        assert order.order_number.startswith("ord_")
        assert order.amount == Decimal("1500.50")
        assert order.status == OrderStatus.PENDING

    def test_state_machine_transitions(self):
        # Valid: PENDING -> CANCELLED
        assert (
            validate_order_status_transition(OrderStatus.PENDING, OrderStatus.CANCELLED)
            is True
        )

        # Invalid: CANCELLED -> PAID must raise BusinessLogicError
        with pytest.raises(BusinessLogicError):
            validate_order_status_transition(OrderStatus.CANCELLED, OrderStatus.PAID)

    def test_auto_expire_pending_orders_task(self):
        merchant_user = UserRepository.create_user(
            email="expire_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        past_time = timezone.now() - timedelta(minutes=10)

        # Create expired order in database
        order = OrderService.create_order(merchant_user, {"amount": "500.00"})
        order.expires_at = past_time
        order.save()

        count = auto_expire_pending_orders_task()
        assert count == 1
        order.refresh_from_db()
        assert order.status == OrderStatus.EXPIRED


@pytest.mark.django_db
class TestOrderAPIEndpoints:
    def test_order_crud_api(self, api_client):
        UserRepository.create_user(
            email="ord_api@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        _, tokens = AuthService.login_user("ord_api@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        url = reverse("orders:order_list_create")
        payload = {
            "amount": "2500.00",
            "currency": "INR",
            "description": "Consulting Fee",
        }
        res = api_client.post(url, payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        order_number = res.json()["data"]["order_number"]

        # Get Order Details
        detail_url = reverse(
            "orders:order_detail", kwargs={"order_identifier": order_number}
        )
        detail_res = api_client.get(detail_url)
        assert detail_res.status_code == status.HTTP_200_OK
        assert detail_res.json()["data"]["amount"] == "2500.00"

        # Cancel Order
        cancel_url = reverse(
            "orders:order_cancel", kwargs={"order_identifier": order_number}
        )
        cancel_res = api_client.post(cancel_url)
        assert cancel_res.status_code == status.HTTP_200_OK
        assert cancel_res.json()["data"]["status"] == OrderStatus.CANCELLED
