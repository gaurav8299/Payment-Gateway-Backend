from typing import Any, Dict

from common.utils import generate_hmac_signature, generate_unique_id
from payments.adapters.base import BasePaymentGatewayAdapter


class StripeAdapterMock(BasePaymentGatewayAdapter):
    """
    Mock Adapter modeling Stripe PaymentIntent and Charge APIs.
    """

    def create_payment(
        self,
        payment_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        metadata: dict,
    ) -> Dict[str, Any]:
        intent_id = generate_unique_id("pi_mock", length=24)
        return {
            "success": True,
            "gateway": "STRIPE",
            "gateway_transaction_id": intent_id,
            "status": "AUTHORIZED",
            "client_secret": f"{intent_id}_secret_test123",
            "message": "Stripe PaymentIntent created & authorized",
        }

    def authorize(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "AUTHORIZED",
        }

    def capture(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        charge_id = generate_unique_id("ch_mock", length=24)
        return {
            "success": True,
            "gateway_transaction_id": charge_id,
            "status": "CAPTURED",
            "message": "Stripe PaymentIntent captured successfully",
        }

    def void(self, gateway_transaction_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "VOIDED",
            "message": "Stripe PaymentIntent canceled",
        }

    def refund(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        refund_id = generate_unique_id("re_mock", length=24)
        return {
            "success": True,
            "gateway_transaction_id": refund_id,
            "status": "REFUNDED",
        }

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        expected = generate_hmac_signature(payload, secret)
        return expected == signature
