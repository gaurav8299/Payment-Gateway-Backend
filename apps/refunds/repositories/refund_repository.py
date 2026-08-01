from decimal import Decimal
from typing import Optional
from uuid import UUID

from customer.models import CustomerProfile
from django.db.models import Q, QuerySet, Sum
from merchant.models import MerchantProfile
from payments.models import Payment
from refunds.models import (
    DeadLetterRefundTask,
    Refund,
    RefundEvent,
    RefundEventType,
    RefundLedger,
    RefundLedgerAction,
    RefundStatus,
)


class RefundRepository:
    """
    Repository class handling data access for Refunds, Ledgers, Events, and DLQ.
    """

    @staticmethod
    def get_by_id(
        refund_id: UUID | str, merchant: Optional[MerchantProfile] = None
    ) -> Optional[Refund]:
        try:
            qs = Refund.objects.all()
            if merchant:
                qs = qs.filter(merchant=merchant)
            return qs.get(id=refund_id)
        except Refund.DoesNotExist:
            return None

    @staticmethod
    def get_by_refund_id_str(
        refund_id_str: str, merchant: Optional[MerchantProfile] = None
    ) -> Optional[Refund]:
        try:
            qs = Refund.objects.all()
            if merchant:
                qs = qs.filter(merchant=merchant)
            return qs.get(refund_id=refund_id_str)
        except Refund.DoesNotExist:
            return None

    @staticmethod
    def get_total_refunded_amount_for_payment(payment: Payment) -> Decimal:
        result = Refund.objects.filter(
            payment=payment,
            status__in=[
                RefundStatus.CREATED,
                RefundStatus.PROCESSING,
                RefundStatus.SUCCESS,
            ],
        ).aggregate(total=Sum("amount"))
        return result["total"] or Decimal("0.00")

    @staticmethod
    def create_refund(
        refund_id_str: str,
        payment: Payment,
        merchant: MerchantProfile,
        amount: Decimal,
        currency: str,
        reason: str = "",
        metadata: Optional[dict] = None,
        requested_by: str = "",
        customer: Optional[CustomerProfile] = None,
    ) -> Refund:
        refund = Refund.objects.create(
            refund_id=refund_id_str,
            payment=payment,
            order=payment.order,
            merchant=merchant,
            customer=customer or payment.customer,
            amount=amount,
            currency=currency.upper(),
            reason=reason,
            status=RefundStatus.CREATED,
            metadata=metadata or {},
            requested_by=requested_by,
        )

        # Log initial ledger entry
        RefundRepository.create_ledger_entry(
            refund=refund,
            action=RefundLedgerAction.REFUND_CREATED,
            amount=amount,
            status=RefundStatus.CREATED,
        )

        # Record domain event
        RefundEvent.objects.create(
            refund=refund,
            event_type=RefundEventType.CREATED,
            payload={
                "refund_id": refund.refund_id,
                "payment_id": payment.payment_id,
                "amount": str(amount),
                "currency": refund.currency,
                "status": refund.status,
            },
        )
        return refund

    @staticmethod
    def create_ledger_entry(
        refund: Refund,
        action: str,
        amount: Decimal,
        status: str,
        gateway_response: Optional[dict] = None,
    ) -> RefundLedger:
        return RefundLedger.objects.create(
            refund=refund,
            action=action,
            amount=amount,
            status=status,
            gateway_response=gateway_response or {},
        )

    @staticmethod
    def update_refund_status(
        refund: Refund,
        new_status: str,
        ledger_action: str,
        gateway_refund_id: str = "",
        failure_code: str = "",
        failure_reason: str = "",
        gateway_response: Optional[dict] = None,
    ) -> Refund:
        refund.status = new_status
        if gateway_refund_id:
            refund.gateway_refund_id = gateway_refund_id
        if failure_code:
            refund.failure_code = failure_code
        if failure_reason:
            refund.failure_reason = failure_reason
        refund.save()

        # Immutable ledger entry
        RefundRepository.create_ledger_entry(
            refund=refund,
            action=ledger_action,
            amount=refund.amount,
            status=new_status,
            gateway_response=gateway_response or {},
        )

        # Map event type
        event_type_map = {
            RefundStatus.PROCESSING: RefundEventType.PROCESSING,
            RefundStatus.SUCCESS: RefundEventType.SUCCEEDED,
            RefundStatus.FAILED: RefundEventType.FAILED,
        }
        if new_status in event_type_map:
            RefundEvent.objects.create(
                refund=refund,
                event_type=event_type_map[new_status],
                payload={
                    "refund_id": refund.refund_id,
                    "status": new_status,
                    "failure_code": failure_code,
                },
            )
        return refund

    @staticmethod
    def list_refunds_queryset(
        merchant: MerchantProfile,
        payment_id: Optional[str] = None,
        status: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> QuerySet:
        qs = Refund.objects.filter(merchant=merchant)
        if payment_id:
            qs = qs.filter(payment__payment_id=payment_id)
        if status:
            qs = qs.filter(status=status)
        if search_query:
            qs = qs.filter(
                Q(refund_id__icontains=search_query)
                | Q(gateway_refund_id__icontains=search_query)
                | Q(payment__payment_id__icontains=search_query)
            )
        return qs

    @staticmethod
    def create_dlq_record(
        refund: Refund, error_message: str, retry_count: int
    ) -> DeadLetterRefundTask:
        return DeadLetterRefundTask.objects.create(
            refund=refund,
            error_message=error_message,
            retry_count=retry_count,
            resolved=False,
        )
