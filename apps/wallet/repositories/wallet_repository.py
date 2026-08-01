from typing import List, Optional
from uuid import UUID

from customer.models import CustomerProfile
from merchant.models import MerchantProfile
from wallet.models import Wallet, WalletStatus, WalletTransaction


class WalletRepository:
    """
    Repository for Wallet data access with atomic row locking routines.
    """

    @staticmethod
    def get_by_id(wallet_id: UUID | str) -> Optional[Wallet]:
        try:
            return Wallet.objects.get(id=wallet_id)
        except Wallet.DoesNotExist:
            return None

    @staticmethod
    def get_or_create_wallet(
        customer: CustomerProfile, merchant: MerchantProfile, currency: str = "INR"
    ) -> Wallet:
        wallet, _ = Wallet.objects.get_or_create(
            customer=customer,
            merchant=merchant,
            currency=currency.upper(),
            defaults={"status": WalletStatus.ACTIVE},
        )
        return wallet

    @staticmethod
    def get_wallet_with_lock(wallet_id: UUID | str) -> Optional[Wallet]:
        """
        Retrieves wallet entity with pessimistic row locking (`select_for_update`).
        Must be executed inside `transaction.atomic()`.
        """
        try:
            return Wallet.objects.select_for_update().get(id=wallet_id)
        except Wallet.DoesNotExist:
            return None

    @staticmethod
    def update_wallet_status(wallet: Wallet, status: str) -> Wallet:
        wallet.status = status
        wallet.save(update_fields=["status", "updated_at"])
        return wallet

    @staticmethod
    def create_transaction(
        transaction_number: str,
        wallet: Wallet,
        amount,
        type: str,
        balance_before,
        balance_after,
        reference: str = "",
        description: str = "",
    ) -> WalletTransaction:
        return WalletTransaction.objects.create(
            transaction_number=transaction_number,
            wallet=wallet,
            amount=amount,
            type=type,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=reference,
            description=description,
        )

    @staticmethod
    def list_transactions(wallet: Wallet) -> List[WalletTransaction]:
        return list(
            WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")
        )
