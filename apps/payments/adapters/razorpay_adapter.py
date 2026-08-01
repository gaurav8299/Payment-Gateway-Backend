from typing import Any, Dict

from common.utils import generate_hmac_signature, generate_unique_id
from payments.adapters.base import BasePaymentGatewayAdapter


class RazorpayAdapterMock(BasePaymentGatewayAdapter):
    """
    Mock Adapter modeling Razorpay Order and Payment Capture APIs.
    """

    def create_payment(
        self,
        payment_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        metadata: dict,
    ) -> Dict[str, Any]:
        rzp_order_id = generate_unique_id("order_rzp", length=20)
        return {
            "success": True,
            "gateway": "RAZORPAY",
            "gateway_transaction_id": rzp_order_id,
            "status": "CREATED",
            "message": "Razorpay Order created successfully",
        }

    def authorize(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        payment_id = generate_unique_id("pay_rzp", length=20)
        return {
            "success": True,
            "gateway_transaction_id": payment_id,
            "status": "AUTHORIZED",
        }

    def capture(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "CAPTURED",
            "message": "Razorpay Payment captured",
        }

    def void(self, gateway_transaction_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "gateway_transaction_id": gateway_transaction_id,
            "status": "VOIDED",
        }

    def refund(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        rfnd_id = generate_unique_id("rfnd_rzp", length=20)
        return {
            "success": True,
            "gateway_transaction_id": rfnd_id,
            "status": "REFUNDED",
        }

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        expected = generate_hmac_signature(payload, secret)
        return expected == signature
