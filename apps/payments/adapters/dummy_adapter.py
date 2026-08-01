from typing import Any, Dict

from common.utils import generate_hmac_signature, generate_unique_id
from payments.adapters.base import BasePaymentGatewayAdapter


class DummyGatewayAdapter(BasePaymentGatewayAdapter):
    """
    Simulated Gateway Adapter providing instant authorization and capture routines.
    """

    def create_payment(
        self,
        payment_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        metadata: dict,
    ) -> Dict[str, Any]:
        tx_id = generate_unique_id("gtx_dummy", length=24)
        return {
            "success": True,
            "gateway": "DUMMY",
            "gateway_transaction_id": tx_id,
            "status": "CAPTURED",
            "message": "Dummy payment captured successfully",
        }

    def authorize(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "AUTHORIZED",
            "message": "Dummy payment authorized",
        }

    def capture(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "CAPTURED",
            "message": "Dummy payment captured",
        }

    def void(self, gateway_transaction_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "VOIDED",
            "message": "Dummy payment voided",
        }

    def refund(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "REFUNDED",
            "message": "Dummy payment refunded",
        }

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        expected = generate_hmac_signature(payload, secret)
        return expected == signature
