from typing import Optional
from uuid import UUID

from customer.models import CustomerProfile
from django.db.models import Q, QuerySet
from merchant.models import MerchantProfile
from orders.models import Order
from payments.models import (
    Payment,
    PaymentEvent,
    PaymentEventType,
    PaymentLedger,
    PaymentLedgerAction,
    PaymentStatus,
)
from wallet.models import Wallet


class PaymentRepository:
    """
    Repository handling data access for Payment entities, immutable ledgers, and events.
    """

    @staticmethod
    def get_by_id(
        payment_id: UUID | str, merchant: Optional[MerchantProfile] = None
    ) -> Optional[Payment]:
        try:
            qs = Payment.objects.all()
            if merchant:
                qs = qs.filter(merchant=merchant)
            return qs.get(id=payment_id)
        except Payment.DoesNotExist:
            return None

    @staticmethod
    def get_by_payment_id_str(
        payment_id_str: str, merchant: Optional[MerchantProfile] = None
    ) -> Optional[Payment]:
        try:
            qs = Payment.objects.all()
            if merchant:
                qs = qs.filter(merchant=merchant)
            return qs.get(payment_id=payment_id_str)
        except Payment.DoesNotExist:
            return None

    @staticmethod
    def create_payment(
        payment_id_str: str,
        order: Order,
        merchant: MerchantProfile,
        amount,
        currency: str,
        payment_method: str,
        gateway: str,
        gateway_transaction_id: str = "",
        customer: Optional[CustomerProfile] = None,
        wallet: Optional[Wallet] = None,
        status: str = PaymentStatus.CREATED,
        metadata: Optional[dict] = None,
    ) -> Payment:
        payment = Payment.objects.create(
            payment_id=payment_id_str,
            order=order,
            merchant=merchant,
            customer=customer,
            wallet=wallet,
            gateway=gateway,
            gateway_transaction_id=gateway_transaction_id,
            amount=amount,
            currency=currency.upper(),
            payment_method=payment_method,
            status=status,
            metadata=metadata or {},
        )

        # Create initial ledger entry
        PaymentRepository.create_ledger_entry(
            payment=payment,
            action=PaymentLedgerAction.PAYMENT_CREATED,
            amount=amount,
            status=status,
            gateway_response={"gateway_transaction_id": gateway_transaction_id},
        )

        # Record domain event
        PaymentEvent.objects.create(
            payment=payment,
            event_type=PaymentEventType.CREATED,
            payload={
                "payment_id": payment.payment_id,
                "order_number": order.order_number,
                "amount": str(amount),
                "currency": payment.currency,
                "status": status,
            },
        )
        return payment

    @staticmethod
    def create_ledger_entry(
        payment: Payment,
        action: str,
        amount,
        status: str,
        gateway_response: Optional[dict] = None,
    ) -> PaymentLedger:
        return PaymentLedger.objects.create(
            payment=payment,
            action=action,
            amount=amount,
            status=status,
            gateway_response=gateway_response or {},
        )

    @staticmethod
    def update_payment_status(
        payment: Payment,
        new_status: str,
        ledger_action: str,
        gateway_transaction_id: str = "",
        failure_code: str = "",
        failure_reason: str = "",
        gateway_response: Optional[dict] = None,
    ) -> Payment:
        payment.status = new_status
        if gateway_transaction_id:
            payment.gateway_transaction_id = gateway_transaction_id
        if failure_code:
            payment.failure_code = failure_code
        if failure_reason:
            payment.failure_reason = failure_reason
        payment.save()

        # Immutable ledger recording
        PaymentRepository.create_ledger_entry(
            payment=payment,
            action=ledger_action,
            amount=payment.amount,
            status=new_status,
            gateway_response=gateway_response or {},
        )

        # Map event type
        event_type_map = {
            PaymentStatus.AUTHORIZED: PaymentEventType.AUTHORIZED,
            PaymentStatus.CAPTURED: PaymentEventType.CAPTURED,
            PaymentStatus.FAILED: PaymentEventType.FAILED,
            PaymentStatus.VOIDED: PaymentEventType.VOIDED,
            PaymentStatus.SETTLED: PaymentEventType.SETTLED,
        }
        if new_status in event_type_map:
            PaymentEvent.objects.create(
                payment=payment,
                event_type=event_type_map[new_status],
                payload={
                    "payment_id": payment.payment_id,
                    "status": new_status,
                    "failure_code": failure_code,
                },
            )
        return payment

    @staticmethod
    def list_payments_queryset(
        merchant: MerchantProfile,
        status: Optional[str] = None,
        gateway: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> QuerySet:
        qs = Payment.objects.filter(merchant=merchant)
        if status:
            qs = qs.filter(status=status)
        if gateway:
            qs = qs.filter(gateway=gateway)
        if search_query:
            qs = qs.filter(
                Q(payment_id__icontains=search_query)
                | Q(gateway_transaction_id__icontains=search_query)
                | Q(order__order_number__icontains=search_query)
            )
        return qs
