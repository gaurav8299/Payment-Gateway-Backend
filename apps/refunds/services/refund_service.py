from decimal import Decimal
from typing import Any, Dict

from accounts.models import User
from common.exceptions import BusinessLogicError, ResourceNotFoundError
from common.utils import generate_unique_id
from django.db.models import Sum
from merchant.services.merchant_service import MerchantService
from payments.models import PaymentStatus
from payments.repositories.payment_repository import PaymentRepository
from refunds.models import DeadLetterRefundTask, Refund, RefundStatus
from refunds.repositories.refund_repository import RefundRepository
from refunds.tasks import process_refund_task


class RefundService:
    """
    Business logic layer for Refund creation, validations, async task dispatching, and metrics.
    """

    @classmethod
    def create_refund(cls, user: User, validated_data: Dict[str, Any]) -> Refund:
        merchant = MerchantService.get_or_create_profile(user)
        payment_identifier = validated_data["payment_id"]

        payment = PaymentRepository.get_by_payment_id_str(payment_identifier, merchant)
        if not payment:
            payment = PaymentRepository.get_by_id(payment_identifier, merchant)
        if not payment:
            raise ResourceNotFoundError(detail="Payment not found.")

        # Payment must be in CAPTURED or SETTLED status
        if payment.status not in [
            PaymentStatus.CAPTURED,
            PaymentStatus.SETTLED,
            "PARTIALLY_REFUNDED",
        ]:
            raise BusinessLogicError(
                detail=f"Cannot refund payment with status '{payment.status}'. Payment must be CAPTURED or SETTLED.",
                code="PAYMENT_NOT_CAPTURED",
            )

        amount = Decimal(str(validated_data["amount"]))
        if amount <= Decimal("0.00"):
            raise BusinessLogicError(
                detail="Refund amount must be greater than 0.", code="INVALID_AMOUNT"
            )

        # Check total existing refunds for this payment
        already_refunded = RefundRepository.get_total_refunded_amount_for_payment(
            payment
        )
        available_for_refund = payment.amount - already_refunded

        if amount > available_for_refund:
            raise BusinessLogicError(
                detail=f"Requested refund amount ({amount} {payment.currency}) exceeds maximum available refundable amount ({available_for_refund} {payment.currency}).",
                code="REFUND_AMOUNT_EXCEEDED",
            )

        refund_id_str = generate_unique_id("rfnd", length=24)

        refund = RefundRepository.create_refund(
            refund_id_str=refund_id_str,
            payment=payment,
            merchant=merchant,
            amount=amount,
            currency=payment.currency,
            reason=validated_data.get("reason", ""),
            metadata=validated_data.get("metadata", {}),
            requested_by=user.email,
        )

        # Dispatch async Celery processing task
        process_refund_task.delay(refund.refund_id)

        return refund

    @classmethod
    def get_refund(cls, user: User, refund_id_str: str) -> Refund:
        merchant = MerchantService.get_or_create_profile(user)
        refund = RefundRepository.get_by_refund_id_str(refund_id_str, merchant)
        if not refund:
            refund = RefundRepository.get_by_id(refund_id_str, merchant)
        if not refund:
            raise ResourceNotFoundError(detail="Refund not found.")
        return refund

    @classmethod
    def get_refund_metrics(cls, user: User) -> Dict[str, Any]:
        merchant = MerchantService.get_or_create_profile(user)
        qs = Refund.objects.filter(merchant=merchant)

        total_count = qs.count()
        success_count = qs.filter(status=RefundStatus.SUCCESS).count()
        failed_count = qs.filter(status=RefundStatus.FAILED).count()
        processing_count = qs.filter(status=RefundStatus.PROCESSING).count()
        total_refunded_amount = qs.filter(status=RefundStatus.SUCCESS).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        dlq_count = DeadLetterRefundTask.objects.filter(
            refund__merchant=merchant, resolved=False
        ).count()

        success_rate = (success_count / total_count * 100) if total_count > 0 else 100.0

        return {
            "merchant_id": str(merchant.id),
            "summary": {
                "total_refunds_requested": total_count,
                "successful_refunds": success_count,
                "failed_refunds": failed_count,
                "processing_refunds": processing_count,
                "total_refunded_amount": float(total_refunded_amount),
                "success_rate_percentage": round(success_rate, 2),
                "unresolved_dlq_records": dlq_count,
            },
        }
