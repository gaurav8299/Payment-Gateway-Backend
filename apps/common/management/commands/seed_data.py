import logging
from decimal import Decimal

from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from customer.services.customer_service import CustomerService
from django.core.management.base import BaseCommand
from django.db import transaction
from merchant.models import MerchantStatus
from merchant.repositories.merchant_repository import MerchantRepository
from merchant.services.merchant_service import MerchantService
from orders.services.order_service import OrderService
from payments.models import PaymentMethod
from payments.services.payment_service import PaymentService
from refunds.services.refund_service import RefundService
from wallet.repositories.wallet_repository import WalletRepository
from wallet.services.wallet_service import WalletService
from webhooks.repositories.webhook_repository import WebhookRepository

logger = logging.getLogger("payment_gateway")


class Command(BaseCommand):
    help = "Seed database with sample Merchants, Customers, Orders, Payments, Refunds, and Wallets for development & demo testing."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING("Seeding Payment Gateway Demo Data...")
        )

        # 1. Create Demo Merchant User & Profile
        merchant_email = "demo_merchant@gateway.com"
        merchant_user = UserRepository.get_by_email(merchant_email)
        if not merchant_user:
            merchant_user = UserRepository.create_user(
                email=merchant_email,
                password="DemoPassword123!",
                role=UserRole.MERCHANT,
                first_name="Acme",
                last_name="Corp",
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created Merchant User: {merchant_email}")
            )

        merchant = MerchantService.get_or_create_profile(merchant_user)
        MerchantRepository.update_merchant_profile(
            merchant=merchant,
            business_name="Acme Global E-Commerce",
            status=MerchantStatus.ACTIVE,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated Merchant Profile: {merchant.business_name} ({merchant.id})"
            )
        )

        # 2. Create Webhook Endpoint
        endpoint, secret = WebhookRepository.create_endpoint(
            merchant=merchant,
            name="Demo Webhook Endpoint",
            url="https://webhook.site/demo-payment-gateway",
            enabled_events=["payment.captured", "refund.processed", "order.created"],
            description="Demo webhook endpoint for local development testing.",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created Webhook Endpoint: {endpoint.endpoint_id} (Secret: {secret})"
            )
        )

        # 3. Create Sample Customers
        cust1 = CustomerService.create_customer(
            merchant_user,
            {
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "phone": "+14155552671",
            },
        )
        cust2 = CustomerService.create_customer(
            merchant_user,
            {
                "name": "Bob Smith",
                "email": "bob@example.com",
                "phone": "+14155552672",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"Created Customers: {cust1.email}, {cust2.email}")
        )

        # 4. Create Saved Payment Methods & Wallets
        pm1 = CustomerService.add_mock_payment_method(
            merchant_user,
            str(cust1.id),
            {
                "type": "CARD",
                "raw_card_number": "4242424242424242",
                "card_brand": "VISA",
                "exp_month": 12,
                "exp_year": 2028,
                "is_default": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"Added Saved Card for Alice: {pm1.masked_card_number}")
        )

        wallet1 = WalletRepository.get_or_create_wallet(cust1, merchant, currency="INR")
        WalletService.credit_wallet(
            str(wallet1.id),
            Decimal("50000.00"),
            description="Initial Demo Balance Top-up",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Funded Customer Wallet: {wallet1.id} with INR 50,000.00"
            )
        )

        # 5. Create Orders, Payments, & Refunds
        # Order 1 - Card Payment (Captured)
        order1 = OrderService.create_order(
            merchant_user,
            {
                "amount": "2500.00",
                "currency": "INR",
                "description": "Premium Subscription Tier 1",
            },
        )
        payment1 = PaymentService.create_payment(
            user=merchant_user,
            validated_data={
                "order_id": order1.order_number,
                "amount": "2500.00",
                "currency": "INR",
                "payment_method": PaymentMethod.CARD,
                "gateway": "DUMMY",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created Captured Payment: {payment1.payment_id} for Order {order1.order_number}"
            )
        )

        # Partial Refund on Payment 1
        refund1 = RefundService.create_refund(
            user=merchant_user,
            validated_data={
                "payment_id": payment1.payment_id,
                "amount": "500.00",
                "reason": "Customer promotional discount adjustment",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"Processed Refund: {refund1.refund_id} for INR 500.00")
        )

        # Order 2 - Wallet Payment (Captured)
        order2 = OrderService.create_order(
            merchant_user,
            {
                "amount": "1200.00",
                "currency": "INR",
                "description": "Digital Goods Purchase",
            },
        )
        payment2 = PaymentService.create_payment(
            user=merchant_user,
            validated_data={
                "order_id": order2.order_number,
                "amount": "1200.00",
                "currency": "INR",
                "payment_method": PaymentMethod.WALLET,
                "gateway": "WALLET",
                "metadata": {"wallet_id": str(wallet1.id)},
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created Wallet Payment: {payment2.payment_id} for Order {order2.order_number}"
            )
        )

        self.stdout.write(self.style.SUCCESS("\nSuccessfully Seeded All Demo Data!"))
