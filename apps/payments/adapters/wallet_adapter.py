from decimal import Decimal
from typing import Any, Dict

from payments.adapters.base import BasePaymentGatewayAdapter
from wallet.services.wallet_service import WalletService


class WalletGatewayAdapter(BasePaymentGatewayAdapter):
    """
    Adapter bridging Payment Engine directly with internal Digital Wallet engine.
    """

    def create_payment(
        self,
        payment_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        metadata: dict,
    ) -> Dict[str, Any]:
        wallet_id = metadata.get("wallet_id")
        if not wallet_id:
            return {
                "success": False,
                "status": "FAILED",
                "failure_code": "MISSING_WALLET_ID",
                "failure_reason": "wallet_id is required in metadata for WALLET payments.",
            }

        try:
            wallet, txn = WalletService.debit_wallet(
                wallet_id=wallet_id,
                amount=Decimal(str(amount)),
                reference=payment_id,
                description=f"Payment {payment_id}",
            )
            return {
                "success": True,
                "gateway": "WALLET",
                "gateway_transaction_id": txn.transaction_number,
                "status": "CAPTURED",
                "message": "Wallet payment processed & debited successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "status": "FAILED",
                "failure_code": "WALLET_DEBIT_FAILED",
                "failure_reason": str(e),
            }

    def authorize(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "AUTHORIZED",
        }

    def capture(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "CAPTURED",
        }

    def void(self, gateway_transaction_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "VOIDED",
        }

    def refund(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "REFUNDED",
        }

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        return True
