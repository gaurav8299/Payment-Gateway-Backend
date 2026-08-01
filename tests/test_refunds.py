from decimal import Decimal

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from common.exceptions import BusinessLogicError
from customer.services.customer_service import CustomerService
from django.urls import reverse
from orders.services.order_service import OrderService
from payments.models import PaymentGateway, PaymentStatus
from payments.services.payment_service import PaymentService
from refunds.models import RefundStatus
from refunds.services.refund_service import RefundService
from refunds.tasks import process_refund_task
from rest_framework import status
from wallet.services.wallet_service import WalletService


@pytest.mark.django_db
class TestRefundServiceAndValidations:
    def test_create_refund_and_amount_exceeded_validation(self):
        merchant_user = UserRepository.create_user(
            email="rfnd_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        order = OrderService.create_order(
            merchant_user, {"amount": "1000.00", "currency": "INR"}
        )
        payment = PaymentService.create_payment(
            merchant_user,
            {
                "order_id": order.order_number,
                "amount": "1000.00",
                "gateway": PaymentGateway.DUMMY,
            },
        )
        assert payment.status == PaymentStatus.CAPTURED

        # Partial refund 400.00
        refund1 = RefundService.create_refund(
            merchant_user,
            {
                "payment_id": payment.payment_id,
                "amount": "400.00",
                "reason": "Customer return",
            },
        )
        assert refund1.id is not None
        assert refund1.amount == Decimal("400.00")

        # Attempt to refund 700.00 (Total = 400 + 700 = 1100 > 1000) must raise BusinessLogicError!
        with pytest.raises(BusinessLogicError):
            RefundService.create_refund(
                merchant_user,
                {"payment_id": payment.payment_id, "amount": "700.00"},
            )

    def test_refund_uncaptured_payment_raises_exception(self):
        merchant_user = UserRepository.create_user(
            email="uncap_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        order = OrderService.create_order(merchant_user, {"amount": "500.00"})
        payment = PaymentService.create_payment(
            merchant_user,
            {
                "order_id": order.order_number,
                "amount": "500.00",
                "gateway": PaymentGateway.STRIPE,
            },
        )
        assert payment.status == PaymentStatus.AUTHORIZED

        with pytest.raises(BusinessLogicError):
            RefundService.create_refund(
                merchant_user, {"payment_id": payment.payment_id, "amount": "500.00"}
            )


@pytest.mark.django_db
class TestAsyncRefundTaskAndWalletIntegration:
    def test_process_refund_task_success_and_wallet_credit(self):
        merchant_user = UserRepository.create_user(
            email="rfnd_w_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        customer = CustomerService.create_customer(
            merchant_user, {"name": "Refund Cust", "email": "rfcust@example.com"}
        )
        wallet = WalletService.get_or_create_wallet(merchant_user, str(customer.id))
        WalletService.credit_wallet(str(wallet.id), Decimal("1000.00"))

        order = OrderService.create_order(
            merchant_user, {"amount": "600.00", "currency": "INR"}
        )
        payment = PaymentService.create_payment(
            merchant_user,
            {
                "order_id": order.order_number,
                "amount": "600.00",
                "gateway": PaymentGateway.WALLET,
                "metadata": {"wallet_id": str(wallet.id)},
            },
        )
        assert payment.status == PaymentStatus.CAPTURED
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("400.00")  # 1000 - 600

        # Request Refund of 600.00
        refund = RefundService.create_refund(
            merchant_user, {"payment_id": payment.payment_id, "amount": "600.00"}
        )

        # Synchronously execute task logic for test
        res = process_refund_task(refund.refund_id)
        assert res is True

        refund.refresh_from_db()
        assert refund.status == RefundStatus.SUCCESS

        payment.refresh_from_db()
        assert payment.status == "FULLY_REFUNDED"

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("1000.00")  # 400 + 600 = 1000 credited back!


@pytest.mark.django_db
class TestRefundAPIEndpointsAndMetrics:
    def test_refund_api_and_metrics(self, api_client):
        merchant_user = UserRepository.create_user(
            email="rfnd_api_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        order = OrderService.create_order(
            merchant_user, {"amount": "800.00", "currency": "INR"}
        )
        payment = PaymentService.create_payment(
            merchant_user,
            {
                "order_id": order.order_number,
                "amount": "800.00",
                "gateway": PaymentGateway.DUMMY,
            },
        )

        _, tokens = AuthService.login_user("rfnd_api_m@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Request Refund API
        url = reverse("refunds:refund_list_create")
        res = api_client.post(
            url,
            {
                "payment_id": payment.payment_id,
                "amount": "800.00",
                "reason": "Defective item",
            },
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED
        refund_id = res.json()["data"]["refund_id"]

        # Run async task
        process_refund_task(refund_id)

        # Get Refund Metrics API
        metrics_url = reverse("refunds:refund_metrics")
        m_res = api_client.get(metrics_url)
        assert m_res.status_code == status.HTTP_200_OK
        summary = m_res.json()["data"]["summary"]
        assert summary["total_refunds_requested"] == 1
        assert summary["successful_refunds"] == 1
        assert summary["total_refunded_amount"] == 800.0
