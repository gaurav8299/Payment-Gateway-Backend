from accounts.permissions import IsMerchantPermission
from common.exceptions import ResourceNotFoundError
from common.response import APIResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from wallet.repositories.wallet_repository import WalletRepository
from wallet.serializers import (
    WalletCreditDebitSerializer,
    WalletSerializer,
    WalletTransactionSerializer,
)
from wallet.services.wallet_service import WalletService


class WalletGetOrCreateView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Get or Create Customer Wallet",
        description="Retrieves existing digital wallet for customer or creates a new wallet in ACTIVE status.",
        responses={200: WalletSerializer},
    )
    def post(self, request, customer_id):
        wallet = WalletService.get_or_create_wallet(request.user, customer_id)
        return APIResponse.success(
            data=WalletSerializer(wallet).data,
            message="Wallet retrieved/created successfully.",
        )


class WalletDetailView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Get Wallet Balance & Details",
        description="Returns balance, currency, and status of a digital wallet.",
        responses={200: WalletSerializer},
    )
    def get(self, request, wallet_id):
        wallet = WalletRepository.get_by_id(wallet_id)
        if not wallet:
            raise ResourceNotFoundError(detail="Wallet not found.")
        return APIResponse.success(
            data=WalletSerializer(wallet).data,
            message="Wallet details retrieved successfully.",
        )


class WalletCreditView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]
    serializer_class = WalletCreditDebitSerializer

    @extend_schema(
        summary="Credit Wallet Balance",
        description="Atomically credits funds to digital wallet balance and logs transaction.",
        request=WalletCreditDebitSerializer,
        responses={200: dict},
    )
    def post(self, request, wallet_id):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        wallet, txn = WalletService.credit_wallet(
            wallet_id=wallet_id,
            amount=serializer.validated_data["amount"],
            reference=serializer.validated_data.get("reference", ""),
            description=serializer.validated_data.get("description", "Wallet Top-up"),
        )
        return APIResponse.success(
            data={
                "wallet": WalletSerializer(wallet).data,
                "transaction": WalletTransactionSerializer(txn).data,
            },
            message="Wallet balance credited successfully.",
        )


class WalletDebitView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]
    serializer_class = WalletCreditDebitSerializer

    @extend_schema(
        summary="Debit Wallet Balance",
        description="Atomically debits funds from digital wallet. Fails if balance is insufficient.",
        request=WalletCreditDebitSerializer,
        responses={200: dict},
    )
    def post(self, request, wallet_id):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        wallet, txn = WalletService.debit_wallet(
            wallet_id=wallet_id,
            amount=serializer.validated_data["amount"],
            reference=serializer.validated_data.get("reference", ""),
            description=serializer.validated_data.get("description", "Wallet Payment"),
        )
        return APIResponse.success(
            data={
                "wallet": WalletSerializer(wallet).data,
                "transaction": WalletTransactionSerializer(txn).data,
            },
            message="Wallet balance debited successfully.",
        )


class WalletFreezeView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Freeze Wallet",
        description="Freezes wallet preventing further credits or debits.",
        responses={200: WalletSerializer},
    )
    def post(self, request, wallet_id):
        wallet = WalletService.freeze_wallet(wallet_id)
        return APIResponse.success(
            data=WalletSerializer(wallet).data,
            message="Wallet frozen successfully.",
        )


class WalletUnfreezeView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Unfreeze Wallet",
        description="Restores wallet to ACTIVE status.",
        responses={200: WalletSerializer},
    )
    def post(self, request, wallet_id):
        wallet = WalletService.unfreeze_wallet(wallet_id)
        return APIResponse.success(
            data=WalletSerializer(wallet).data,
            message="Wallet unfrozen successfully.",
        )


class WalletTransactionHistoryView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Wallet Transaction History",
        description="Returns audit trail of all financial transactions for a wallet.",
        responses={200: WalletTransactionSerializer(many=True)},
    )
    def get(self, request, wallet_id):
        wallet = WalletRepository.get_by_id(wallet_id)
        if not wallet:
            raise ResourceNotFoundError(detail="Wallet not found.")
        txns = WalletRepository.list_transactions(wallet)
        serializer = WalletTransactionSerializer(txns, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="Wallet transaction history retrieved successfully.",
        )
