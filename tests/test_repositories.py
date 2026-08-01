from decimal import Decimal

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from customer.services.customer_service import CustomerService
from merchant.services.merchant_service import MerchantService
from notifications.models import Notification, NotificationChannel, NotificationStatus
from notifications.repositories.notification_repository import NotificationRepository
from orders.models import OrderStatus
from orders.repositories.order_repository import OrderRepository
from payments.models import PaymentMethod, PaymentStatus
from payments.repositories.payment_repository import PaymentRepository
from refunds.models import RefundLedgerAction, RefundStatus
from refunds.repositories.refund_repository import RefundRepository
from wallet.models import WalletTransactionType
from wallet.repositories.wallet_repository import WalletRepository
from webhooks.models import OutboxEvent
from webhooks.repositories.webhook_repository import WebhookRepository


@pytest.mark.django_db
class TestNotificationRepository:
    def test_notification_repository_crud(self):
        UserRepository.create_user(
            email="notif_repo@example.com",
            password="Password123!",
            role=UserRole.CUSTOMER,
        )
        notif = Notification.objects.create(
            notification_id="notif_test_123",
            recipient="notif_repo@example.com",
            subject="Test Notification",
            template_name="welcome_email",
            channel=NotificationChannel.EMAIL,
        )
        assert notif.id is not None
        assert notif.status == NotificationStatus.PENDING

        fetched = NotificationRepository.get_by_id("notif_test_123")
        assert fetched.id == notif.id

        notifs = NotificationRepository.list_notifications(
            recipient="notif_repo@example.com"
        )
        assert len(notifs) == 1


@pytest.mark.django_db
class TestOrderRepository:
    def test_order_repository_queries(self):
        merchant_user = UserRepository.create_user(
            email="ord_repo_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)

        order1 = OrderRepository.create_order(
            order_number="ord_test_1001",
            merchant=merchant,
            amount=Decimal("500.00"),
            currency="INR",
            description="Order 1",
        )
        OrderRepository.create_order(
            order_number="ord_test_1002",
            merchant=merchant,
            amount=Decimal("1000.00"),
            currency="INR",
            description="Order 2",
        )

        assert OrderRepository.get_by_id(order1.id) == order1
        assert OrderRepository.get_by_order_number("ord_test_1001") == order1

        merchant_orders = OrderRepository.list_orders_queryset(merchant)
        assert merchant_orders.count() == 2

        OrderRepository.update_order_status(order1, OrderStatus.PAID)
        order1.refresh_from_db()
        assert order1.status == OrderStatus.PAID


@pytest.mark.django_db
class TestPaymentRepository:
    def test_payment_repository_queries(self):
        merchant_user = UserRepository.create_user(
            email="pay_repo_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        order = OrderRepository.create_order(
            order_number="ord_pay_test",
            merchant=merchant,
            amount=Decimal("2000.00"),
            currency="INR",
        )

        payment = PaymentRepository.create_payment(
            payment_id_str="pay_test_2001",
            order=order,
            merchant=merchant,
            amount=Decimal("2000.00"),
            currency="INR",
            payment_method=PaymentMethod.CARD,
            gateway="DUMMY",
        )

        assert PaymentRepository.get_by_id(payment.id) == payment
        assert PaymentRepository.get_by_payment_id_str("pay_test_2001") == payment

        merchant_payments = PaymentRepository.list_payments_queryset(merchant)
        assert merchant_payments.count() == 1

        PaymentRepository.update_payment_status(
            payment=payment,
            new_status=PaymentStatus.CAPTURED,
            ledger_action="PAYMENT_CAPTURED",
            gateway_transaction_id="gw_12345",
        )
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CAPTURED
        assert payment.gateway_transaction_id == "gw_12345"


@pytest.mark.django_db
class TestRefundRepository:
    def test_refund_repository_queries(self):
        merchant_user = UserRepository.create_user(
            email="ref_repo_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        order = OrderRepository.create_order(
            order_number="ord_ref_test",
            merchant=merchant,
            amount=Decimal("3000.00"),
            currency="INR",
        )
        payment = PaymentRepository.create_payment(
            payment_id_str="pay_ref_test",
            order=order,
            merchant=merchant,
            amount=Decimal("3000.00"),
            currency="INR",
            payment_method=PaymentMethod.CARD,
            gateway="DUMMY",
        )

        refund = RefundRepository.create_refund(
            refund_id_str="ref_test_3001",
            payment=payment,
            merchant=merchant,
            amount=Decimal("1000.00"),
            currency="INR",
            reason="Customer request",
        )

        assert RefundRepository.get_by_id(refund.id) == refund
        assert RefundRepository.get_by_refund_id_str("ref_test_3001") == refund

        merchant_refunds = RefundRepository.list_refunds_queryset(merchant)
        assert merchant_refunds.count() == 1

        total_refunded = RefundRepository.get_total_refunded_amount_for_payment(payment)
        assert total_refunded == Decimal("1000.00")

        RefundRepository.update_refund_status(
            refund=refund,
            new_status=RefundStatus.SUCCESS,
            ledger_action=RefundLedgerAction.REFUND_SUCCESS,
            gateway_refund_id="ref_gw_123",
        )
        refund.refresh_from_db()
        assert refund.status == RefundStatus.SUCCESS


@pytest.mark.django_db
class TestWalletRepository:
    def test_wallet_repository_operations(self):
        merchant_user = UserRepository.create_user(
            email="wallet_repo_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)
        customer = CustomerService.create_customer(
            merchant_user,
            {"name": "Wallet Customer", "email": "wallet_cust_repo@example.com"},
        )

        wallet = WalletRepository.get_or_create_wallet(
            customer, merchant, currency="INR"
        )
        assert wallet.balance == Decimal("0.00")

        tx1 = WalletRepository.create_transaction(
            transaction_number="txn_12345",
            wallet=wallet,
            amount=Decimal("5000.00"),
            type=WalletTransactionType.CREDIT,
            balance_before=Decimal("0.00"),
            balance_after=Decimal("5000.00"),
            description="Initial top-up",
        )
        assert tx1.id is not None

        txs = WalletRepository.list_transactions(wallet)
        assert len(txs) == 1


@pytest.mark.django_db
class TestWebhookRepository:
    def test_webhook_repository_queries(self):
        merchant_user = UserRepository.create_user(
            email="wh_repo_m@example.com",
            password="Password123!",
            role=UserRole.MERCHANT,
        )
        merchant = MerchantService.get_or_create_profile(merchant_user)

        endpoint, _ = WebhookRepository.create_endpoint(
            merchant=merchant,
            name="Repo Endpoint",
            url="https://example.com/wh",
            enabled_events=["payment.captured"],
        )

        assert (
            WebhookRepository.get_endpoint_by_id(str(endpoint.endpoint_id)) == endpoint
        )

        outbox = OutboxEvent.objects.create(
            event_id="evt_repo_123",
            merchant=merchant,
            event_type="payment.captured",
            resource_type="payment",
            resource_id="pay_123",
            payload={"test": "data"},
            processed=False,
        )
        assert outbox.processed is False

        unprocessed = OutboxEvent.objects.filter(processed=False)
        assert outbox in unprocessed

        outbox.processed = True
        outbox.save()
        outbox.refresh_from_db()
        assert outbox.processed is True
