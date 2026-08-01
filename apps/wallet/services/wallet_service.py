from decimal import Decimal
from typing import Tuple

from accounts.models import User
from common.exceptions import (
    BusinessLogicError,
    InsufficientWalletBalanceError,
    ResourceNotFoundError,
)
from common.utils import generate_unique_id
from customer.services.customer_service import CustomerService
from django.db import transaction
from merchant.services.merchant_service import MerchantService
from wallet.models import Wallet, WalletStatus, WalletTransaction, WalletTransactionType
from wallet.repositories.wallet_repository import WalletRepository


class WalletService:
    """
    Service layer providing thread-safe and atomic Digital Wallet transactions.
    Uses pessimistic database locking (select_for_update) and transaction.atomic().
    """

    @classmethod
    def get_or_create_wallet(
        cls, merchant_user: User, customer_id: str, currency: str = "INR"
    ) -> Wallet:
        merchant = MerchantService.get_or_create_profile(merchant_user)
        customer = CustomerService.get_customer(merchant_user, customer_id)
        return WalletRepository.get_or_create_wallet(customer, merchant, currency)

    @classmethod
    def credit_wallet(
        cls,
        wallet_id: str,
        amount: Decimal,
        reference: str = "",
        description: str = "Wallet Top-up",
        txn_type: str = WalletTransactionType.CREDIT,
    ) -> Tuple[Wallet, WalletTransaction]:
        amount = Decimal(str(amount))
        if amount <= Decimal("0.00"):
            raise BusinessLogicError(
                detail="Credit amount must be greater than zero.", code="INVALID_AMOUNT"
            )

        with transaction.atomic():
            wallet = WalletRepository.get_wallet_with_lock(wallet_id)
            if not wallet:
                raise ResourceNotFoundError(detail="Wallet not found.")

            if wallet.status != WalletStatus.ACTIVE:
                raise BusinessLogicError(
                    detail=f"Cannot credit wallet with status '{wallet.status}'.",
                    code="WALLET_NOT_ACTIVE",
                )

            balance_before = wallet.balance
            balance_after = balance_before + amount

            wallet.balance = balance_after
            wallet.save(update_fields=["balance", "updated_at"])

            txn_number = generate_unique_id("txn", length=24)
            txn = WalletRepository.create_transaction(
                transaction_number=txn_number,
                wallet=wallet,
                amount=amount,
                type=txn_type,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=description,
            )

            return wallet, txn

    @classmethod
    def debit_wallet(
        cls,
        wallet_id: str,
        amount: Decimal,
        reference: str = "",
        description: str = "Wallet Payment Deduction",
        txn_type: str = WalletTransactionType.DEBIT,
    ) -> Tuple[Wallet, WalletTransaction]:
        amount = Decimal(str(amount))
        if amount <= Decimal("0.00"):
            raise BusinessLogicError(
                detail="Debit amount must be greater than zero.", code="INVALID_AMOUNT"
            )

        with transaction.atomic():
            wallet = WalletRepository.get_wallet_with_lock(wallet_id)
            if not wallet:
                raise ResourceNotFoundError(detail="Wallet not found.")

            if wallet.status != WalletStatus.ACTIVE:
                raise BusinessLogicError(
                    detail=f"Cannot debit wallet with status '{wallet.status}'.",
                    code="WALLET_NOT_ACTIVE",
                )

            if wallet.balance < amount:
                raise InsufficientWalletBalanceError(
                    detail=f"Insufficient wallet balance ({wallet.balance} {wallet.currency}). Requested deduction: {amount} {wallet.currency}."
                )

            balance_before = wallet.balance
            balance_after = balance_before - amount

            wallet.balance = balance_after
            wallet.save(update_fields=["balance", "updated_at"])

            txn_number = generate_unique_id("txn", length=24)
            txn = WalletRepository.create_transaction(
                transaction_number=txn_number,
                wallet=wallet,
                amount=amount,
                type=txn_type,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=description,
            )

            return wallet, txn

    @classmethod
    def freeze_wallet(cls, wallet_id: str) -> Wallet:
        wallet = WalletRepository.get_by_id(wallet_id)
        if not wallet:
            raise ResourceNotFoundError(detail="Wallet not found.")
        return WalletRepository.update_wallet_status(wallet, WalletStatus.FROZEN)

    @classmethod
    def unfreeze_wallet(cls, wallet_id: str) -> Wallet:
        wallet = WalletRepository.get_by_id(wallet_id)
        if not wallet:
            raise ResourceNotFoundError(detail="Wallet not found.")
        return WalletRepository.update_wallet_status(wallet, WalletStatus.ACTIVE)
