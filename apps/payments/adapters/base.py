from abc import ABC, abstractmethod
from typing import Any, Dict


class BasePaymentGatewayAdapter(ABC):
    """
    Abstract Interface for Payment Gateway Adapters.
    Encapsulates vendor-specific payment interactions.
    """

    @abstractmethod
    def create_payment(
        self,
        payment_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        metadata: dict,
    ) -> Dict[str, Any]:
        """
        Create payment intent / order on upstream gateway.
        """

    @abstractmethod
    def authorize(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        """
        Authorize payment amount.
        """

    @abstractmethod
    def capture(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        """
        Capture authorized payment amount.
        """

    @abstractmethod
    def void(self, gateway_transaction_id: str) -> Dict[str, Any]:
        """
        Void authorized payment.
        """

    @abstractmethod
    def refund(self, gateway_transaction_id: str, amount: float) -> Dict[str, Any]:
        """
        Refund captured payment (placeholder for Phase 6).
        """

    @abstractmethod
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Verify gateway HMAC signature.
        """
