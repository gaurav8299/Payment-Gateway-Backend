from decimal import Decimal

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from common.exceptions import BusinessLogicError
from customer.services.customer_service import CustomerService
from django.urls import reverse
from orders.models import OrderStatus
from orders.services.order_service import OrderService
from payments.adapters import (
    DummyGatewayAdapter,
    RazorpayAdapterMock,
    StripeAdapterMock,
    WalletGatewayAdapter,
)
from payments.factories import PaymentGatewayFactory
from payments.models import Payment, PaymentGateway, PaymentMethod, PaymentStatus
from payments.services.payment_service import PaymentService
from rest_framework import status
from wallet.services.wallet_service import WalletService


@pytest.mark.django_db
class TestPaymentAdaptersAndFactory:
    def test_factory_returns_correct_adapters(self):
        assert isinstance(
            PaymentGatewayFactory.get_adapter("DUMMY"), DummyGatewayAdapter
        )
        assert isinstance(
            PaymentGatewayFactory.get_adapter("STRIPE"), StripeAdapterMock
        )
        assert isinstance(
            PaymentGatewayFactory.get_adapter("RAZORPAY"), RazorpayAdapterMock
        )
        assert isinstance(
            PaymentGatewayFactory.get_adapter("WALLET"), WalletGatewayAdapter
        )

    def test_factory_invalid_gateway_raises_exception(self):
        with pytest.raises(BusinessLogicError):
            PaymentGatewayFactory.get_adapter("INVALID_GATEWAY")


@pytest.mark.django_db
class TestPaymentServiceAndStateMachine:
    def test_create_and_capture_dummy_payment(self):
        merchant_user = UserRepository.create_user(
            email="pay_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        order = OrderService.create_order(
            merchant_user, {"amount": "1000.00", "currency": "INR"}
        )

        pay_data = {
            "order_id": order.order_number,
            "amount": "1000.00",
            "currency": "INR",
            "gateway": PaymentGateway.DUMMY,
            "payment_method": PaymentMethod.CARD,
        }
        payment = PaymentService.create_payment(merchant_user, pay_data)
        assert payment.id is not None
        assert payment.payment_id.startswith("pay_")
        assert payment.status == PaymentStatus.CAPTURED

        # Order must be automatically synced to PAID
        order.refresh_from_db()
        assert order.status == OrderStatus.PAID

    def test_create_stripe_payment_and_capture(self):
        merchant_user = UserRepository.create_user(
            email="stripe_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        order = OrderService.create_order(
            merchant_user, {"amount": "500.00", "currency": "INR"}
        )

        pay_data = {
            "order_id": order.order_number,
            "amount": "500.00",
            "currency": "INR",
            "gateway": PaymentGateway.STRIPE,
            "payment_method": PaymentMethod.CARD,
        }
        payment = PaymentService.create_payment(merchant_user, pay_data)
        assert payment.status == PaymentStatus.AUTHORIZED

        order.refresh_from_db()
        assert order.status == OrderStatus.PROCESSING

        # Capture payment
        captured_payment = PaymentService.capture_payment(
            merchant_user, payment.payment_id
        )
        assert captured_payment.status == PaymentStatus.CAPTURED

        order.refresh_from_db()
        assert order.status == OrderStatus.PAID

    def test_void_authorized_payment(self):
        merchant_user = UserRepository.create_user(
            email="void_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        order = OrderService.create_order(
            merchant_user, {"amount": "300.00", "currency": "INR"}
        )

        payment = PaymentService.create_payment(
            merchant_user,
            {
                "order_id": order.order_number,
                "amount": "300.00",
                "gateway": PaymentGateway.STRIPE,
            },
        )
        assert payment.status == PaymentStatus.AUTHORIZED

        voided_payment = PaymentService.void_payment(merchant_user, payment.payment_id)
        assert voided_payment.status == PaymentStatus.VOIDED

        order.refresh_from_db()
        assert order.status == OrderStatus.CANCELLED

    def test_wallet_payment_integration(self):
        merchant_user = UserRepository.create_user(
            email="wpay_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        customer = CustomerService.create_customer(
            merchant_user, {"name": "WPay Cust", "email": "wpay@example.com"}
        )
        wallet = WalletService.get_or_create_wallet(merchant_user, str(customer.id))
        WalletService.credit_wallet(str(wallet.id), Decimal("1000.00"))

        order = OrderService.create_order(
            merchant_user, {"amount": "400.00", "currency": "INR"}
        )

        payment = PaymentService.create_payment(
            merchant_user,
            {
                "order_id": order.order_number,
                "amount": "400.00",
                "gateway": PaymentGateway.WALLET,
                "payment_method": PaymentMethod.WALLET,
                "metadata": {"wallet_id": str(wallet.id)},
            },
        )
        assert payment.status == PaymentStatus.CAPTURED

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("600.00")  # 1000 - 400 = 600


@pytest.mark.django_db
class TestPaymentAPIAndIdempotency:
    def test_payment_idempotency_deduplication(self, api_client):
        merchant_user = UserRepository.create_user(
            email="idemp_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        order = OrderService.create_order(
            merchant_user, {"amount": "1200.00", "currency": "INR"}
        )

        _, tokens = AuthService.login_user("idemp_m@example.com", "Password123!")
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
            HTTP_IDEMPOTENCY_KEY="idempotency-key-test-12345",
        )

        url = reverse("payments:payment_list_create")
        payload = {
            "order_id": order.order_number,
            "amount": "1200.00",
            "currency": "INR",
            "gateway": "DUMMY",
            "payment_method": "CARD",
        }

        # First request
        res1 = api_client.post(url, payload, format="json")
        assert res1.status_code == status.HTTP_201_CREATED
        payment_id1 = res1.json()["data"]["payment_id"]

        # Duplicate request with same Idempotency-Key
        res2 = api_client.post(url, payload, format="json")
        assert res2.status_code == status.HTTP_201_CREATED
        payment_id2 = res2.json()["data"]["payment_id"]

        # Identical response payload returned without creating duplicate payment!
        assert payment_id1 == payment_id2
        assert Payment.objects.filter(order=order).count() == 1
