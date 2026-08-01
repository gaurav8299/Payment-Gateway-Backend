from decimal import Decimal

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from common.exceptions import BusinessLogicError, InsufficientWalletBalanceError
from customer.services.customer_service import CustomerService
from django.urls import reverse
from rest_framework import status
from wallet.models import WalletStatus, WalletTransactionType
from wallet.services.wallet_service import WalletService


@pytest.mark.django_db
class TestWalletServiceAndAtomicity:
    def test_get_or_create_wallet(self):
        merchant_user = UserRepository.create_user(
            email="wallet_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        customer = CustomerService.create_customer(
            merchant_user, {"name": "Wallet Cust", "email": "wcust@example.com"}
        )

        wallet = WalletService.get_or_create_wallet(merchant_user, str(customer.id))
        assert wallet.id is not None
        assert wallet.balance == Decimal("0.00")
        assert wallet.status == WalletStatus.ACTIVE

    def test_credit_and_debit_wallet(self):
        merchant_user = UserRepository.create_user(
            email="cd_m@example.com", password="Password123!", role=UserRole.MERCHANT
        )
        customer = CustomerService.create_customer(
            merchant_user, {"name": "CD Cust", "email": "cdcust@example.com"}
        )
        wallet = WalletService.get_or_create_wallet(merchant_user, str(customer.id))

        # Credit 1000.00
        w_credited, txn_c = WalletService.credit_wallet(
            str(wallet.id), Decimal("1000.00"), description="Top-up"
        )
        assert w_credited.balance == Decimal("1000.00")
        assert txn_c.transaction_number.startswith("txn_")
        assert txn_c.type == WalletTransactionType.CREDIT

        # Debit 400.00
        w_debited, txn_d = WalletService.debit_wallet(
            str(wallet.id), Decimal("400.00"), description="Payment"
        )
        assert w_debited.balance == Decimal("600.00")
        assert txn_d.balance_after == Decimal("600.00")

    def test_debit_insufficient_balance_raises_exception(self):
        merchant_user = UserRepository.create_user(
            email="insuff_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        customer = CustomerService.create_customer(
            merchant_user, {"name": "Insuff Cust", "email": "insuff@example.com"}
        )
        wallet = WalletService.get_or_create_wallet(merchant_user, str(customer.id))

        # Attempt to debit 100.00 from 0.00 balance
        with pytest.raises(InsufficientWalletBalanceError):
            WalletService.debit_wallet(str(wallet.id), Decimal("100.00"))

        wallet.refresh_from_db()
        assert wallet.balance == Decimal("0.00")  # Balance remains untouched

    def test_frozen_wallet_blocks_transactions(self):
        merchant_user = UserRepository.create_user(
            email="freeze_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        customer = CustomerService.create_customer(
            merchant_user, {"name": "Freeze Cust", "email": "fcust@example.com"}
        )
        wallet = WalletService.get_or_create_wallet(merchant_user, str(customer.id))

        WalletService.freeze_wallet(str(wallet.id))

        with pytest.raises(BusinessLogicError):
            WalletService.credit_wallet(str(wallet.id), Decimal("500.00"))


@pytest.mark.django_db
class TestWalletAPIEndpoints:
    def test_wallet_api_credit_debit_and_history(self, api_client):
        merchant_user = UserRepository.create_user(
            email="wallet_api_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        customer = CustomerService.create_customer(
            merchant_user, {"name": "API Wallet Cust", "email": "apiw@example.com"}
        )

        _, tokens = AuthService.login_user("wallet_api_m@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        # Create wallet
        init_url = reverse(
            "wallet:wallet_customer", kwargs={"customer_id": str(customer.id)}
        )
        init_res = api_client.post(init_url)
        assert init_res.status_code == status.HTTP_200_OK
        wallet_id = init_res.json()["data"]["id"]

        # Credit wallet API
        credit_url = reverse("wallet:wallet_credit", kwargs={"wallet_id": wallet_id})
        c_res = api_client.post(
            credit_url, {"amount": "750.00", "description": "API Credit"}, format="json"
        )
        assert c_res.status_code == status.HTTP_200_OK
        assert c_res.json()["data"]["wallet"]["balance"] == "750.00"

        # History API
        txns_url = reverse(
            "wallet:wallet_transactions", kwargs={"wallet_id": wallet_id}
        )
        t_res = api_client.get(txns_url)
        assert t_res.status_code == status.HTTP_200_OK
        assert len(t_res.json()["data"]) == 1
