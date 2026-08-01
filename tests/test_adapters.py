import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from payments.adapters.dummy_adapter import DummyGatewayAdapter
from payments.adapters.razorpay_adapter import RazorpayAdapterMock
from payments.adapters.stripe_adapter import StripeAdapterMock
from payments.adapters.wallet_adapter import WalletGatewayAdapter
from payments.factories import PaymentGatewayFactory
from payments.models import PaymentGateway


@pytest.mark.django_db
class TestPaymentAdapters:
    def test_dummy_adapter(self):
        adapter = DummyGatewayAdapter()
        res = adapter.create_payment(
            payment_id="pay_123",
            amount=1000.0,
            currency="INR",
            payment_method="CARD",
            metadata={},
        )
        assert res["success"] is True
        assert res["status"] == "CAPTURED"

        auth = adapter.authorize(res["gateway_transaction_id"], 1000.0)
        assert auth["success"] is True

        cap = adapter.capture(res["gateway_transaction_id"], 1000.0)
        assert cap["success"] is True

        void_res = adapter.void(res["gateway_transaction_id"])
        assert void_res["success"] is True

        ref = adapter.refund(res["gateway_transaction_id"], 500.0)
        assert ref["success"] is True

        sig_valid = adapter.verify_signature("payload", "sig", "secret")
        assert isinstance(sig_valid, bool)

    def test_stripe_adapter_mock(self):
        adapter = StripeAdapterMock()
        res = adapter.create_payment(
            payment_id="pay_stripe_1",
            amount=2500.0,
            currency="USD",
            payment_method="CARD",
            metadata={},
        )
        assert res["success"] is True
        assert res["gateway"] == "STRIPE"

        auth = adapter.authorize(res["gateway_transaction_id"], 2500.0)
        assert auth["success"] is True

        cap = adapter.capture(res["gateway_transaction_id"], 2500.0)
        assert cap["success"] is True

        ref = adapter.refund(res["gateway_transaction_id"], 1000.0)
        assert ref["success"] is True

    def test_razorpay_adapter_mock(self):
        adapter = RazorpayAdapterMock()
        res = adapter.create_payment(
            payment_id="pay_rzp_1",
            amount=5000.0,
            currency="INR",
            payment_method="UPI",
            metadata={},
        )
        assert res["success"] is True
        assert res["gateway"] == "RAZORPAY"

        auth = adapter.authorize(res["gateway_transaction_id"], 5000.0)
        assert auth["success"] is True

        cap = adapter.capture(res["gateway_transaction_id"], 5000.0)
        assert cap["success"] is True

        ref = adapter.refund(res["gateway_transaction_id"], 2000.0)
        assert ref["success"] is True

    def test_wallet_gateway_adapter(self):
        merchant_user = UserRepository.create_user(
            email="wallet_adapter_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        from customer.services.customer_service import CustomerService
        from merchant.services.merchant_service import MerchantService
        from wallet.repositories.wallet_repository import WalletRepository
        from wallet.services.wallet_service import WalletService

        customer = CustomerService.create_customer(
            merchant_user,
            {"name": "Wallet Cust", "email": "wallet_cust_adapter@example.com"},
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        wallet = WalletRepository.get_or_create_wallet(
            customer, merchant, currency="INR"
        )
        WalletService.credit_wallet(str(wallet.id), 10000.0)

        adapter = WalletGatewayAdapter()
        res = adapter.create_payment(
            payment_id="pay_w_1",
            amount=3000.0,
            currency="INR",
            payment_method="WALLET",
            metadata={"wallet_id": str(wallet.id)},
        )
        assert res["success"] is True
        assert res["gateway"] == "WALLET"

    def test_payment_gateway_factory(self):
        stripe_adapter = PaymentGatewayFactory.get_adapter(PaymentGateway.STRIPE)
        assert isinstance(stripe_adapter, StripeAdapterMock)

        rzp_adapter = PaymentGatewayFactory.get_adapter(PaymentGateway.RAZORPAY)
        assert isinstance(rzp_adapter, RazorpayAdapterMock)

        dummy_adapter = PaymentGatewayFactory.get_adapter(PaymentGateway.DUMMY)
        assert isinstance(dummy_adapter, DummyGatewayAdapter)

        wallet_adapter = PaymentGatewayFactory.get_adapter(PaymentGateway.WALLET)
        assert isinstance(wallet_adapter, WalletGatewayAdapter)

        with pytest.raises(Exception):
            PaymentGatewayFactory.get_adapter("INVALID_GATEWAY")
