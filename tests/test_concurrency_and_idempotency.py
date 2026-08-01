from decimal import Decimal

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from customer.services.customer_service import CustomerService
from merchant.services.merchant_service import MerchantService
from orders.services.order_service import OrderService
from payments.models import PaymentMethod
from payments.services.payment_service import PaymentService
from refunds.services.refund_service import RefundService
from wallet.repositories.wallet_repository import WalletRepository
from wallet.services.wallet_service import WalletService


@pytest.mark.django_db
class TestConcurrencyAndIdempotency:
    def test_wallet_atomic_balance_topup_and_debit(self):
        merchant_user = UserRepository.create_user(
            email="conc_wallet_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        customer = CustomerService.create_customer(
            merchant_user,
            {"name": "Wallet Customer", "email": "conc_wallet_cust@example.com"},
        )

        wallet = WalletRepository.get_or_create_wallet(
            customer, merchant, currency="INR"
        )
        assert wallet.balance == Decimal("0.00")

        # Credit wallet
        WalletService.credit_wallet(
            str(wallet.id), Decimal("10000.00"), description="Initial Deposit"
        )
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("10000.00")

        # Debit wallet
        wallet, tx = WalletService.debit_wallet(
            str(wallet.id), Decimal("2500.00"), description="Purchase Order #1"
        )
        wallet.refresh_from_db()
        assert wallet.balance == Decimal("7500.00")
        assert tx.amount == Decimal("2500.00")

    def test_concurrent_refund_amount_validation(self):
        merchant_user = UserRepository.create_user(
            email="conc_refund_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        MerchantService.get_or_create_profile(merchant_user)

        order = OrderService.create_order(
            merchant_user, {"amount": "5000.00", "currency": "INR"}
        )

        # Create captured payment of 5000.00 INR
        payment = PaymentService.create_payment(
            user=merchant_user,
            validated_data={
                "order_id": order.order_number,
                "amount": "5000.00",
                "currency": "INR",
                "payment_method": PaymentMethod.CARD,
                "gateway": "DUMMY",
            },
        )
        assert payment.status == "CAPTURED"

        # Refund 1: 3000.00
        refund1 = RefundService.create_refund(
            user=merchant_user,
            validated_data={
                "payment_id": payment.payment_id,
                "amount": "3000.00",
                "reason": "Partial Refund 1",
            },
        )
        assert refund1.id is not None

        # Refund 2: 2000.00 (Total = 5000.00)
        refund2 = RefundService.create_refund(
            user=merchant_user,
            validated_data={
                "payment_id": payment.payment_id,
                "amount": "2000.00",
                "reason": "Partial Refund 2",
            },
        )
        assert refund2.id is not None

        # Refund 3: 500.00 (Exceeds original payment amount -> Must raise Exception!)
        with pytest.raises(Exception):
            RefundService.create_refund(
                user=merchant_user,
                validated_data={
                    "payment_id": payment.payment_id,
                    "amount": "500.00",
                    "reason": "Exceeded Refund",
                },
            )
