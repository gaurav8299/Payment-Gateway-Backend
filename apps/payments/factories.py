from common.exceptions import BusinessLogicError
from payments.adapters import (
    BasePaymentGatewayAdapter,
    DummyGatewayAdapter,
    RazorpayAdapterMock,
    StripeAdapterMock,
    WalletGatewayAdapter,
)
from payments.models import PaymentGateway


class PaymentGatewayFactory:
    """
    Factory class producing concrete Payment Gateway Adapters.
    Eliminates if/else branching inside business service layer.
    """

    _adapters = {
        PaymentGateway.DUMMY: DummyGatewayAdapter,
        PaymentGateway.STRIPE: StripeAdapterMock,
        PaymentGateway.RAZORPAY: RazorpayAdapterMock,
        PaymentGateway.WALLET: WalletGatewayAdapter,
        PaymentGateway.COD: DummyGatewayAdapter,
    }

    @classmethod
    def get_adapter(cls, gateway: str) -> BasePaymentGatewayAdapter:
        gateway_upper = (gateway or "DUMMY").upper()
        adapter_class = cls._adapters.get(gateway_upper)

        if not adapter_class:
            raise BusinessLogicError(
                detail=f"Unsupported payment gateway '{gateway}'. Supported gateways: {list(cls._adapters.keys())}",
                code="UNSUPPORTED_GATEWAY",
            )

        return adapter_class()
