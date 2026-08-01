import logging

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from payments.factories import PaymentGatewayFactory
from payments.models import PaymentGateway
from refunds.models import Refund, RefundLedgerAction, RefundStatus
from refunds.repositories.refund_repository import RefundRepository
from wallet.services.wallet_service import WalletService

logger = logging.getLogger("payment_gateway")


@shared_task(bind=True, queue="refund_processing", max_retries=3, default_retry_delay=5)
def process_refund_task(self, refund_id_str: str):
    """
    Asynchronous Celery task processing payment refunds with Redis distributed locking,
    exponential backoff retries, and Dead Letter Queue (DLQ) tracking on failure.
    """
    logger.info(f"Processing async refund task for: {refund_id_str}")
    refund = RefundRepository.get_by_refund_id_str(refund_id_str)
    if not refund:
        logger.error(f"Refund entity '{refund_id_str}' not found.")
        return False

    if refund.status in [RefundStatus.SUCCESS, RefundStatus.FAILED]:
        logger.info(
            f"Refund '{refund_id_str}' already in terminal state '{refund.status}'. Skipping."
        )
        return True

    # Redis Distributed Lock to prevent concurrent processing of refunds for the same payment
    lock_key = f"lock:refund:payment:{refund.payment.id}"
    lock_acquired = cache.add(lock_key, "locked", timeout=30)

    if not lock_acquired:
        logger.warning(
            f"Lock active for payment '{refund.payment.payment_id}'. Retrying refund task..."
        )
        raise self.retry(countdown=2**self.request.retries)

    try:
        # Transition Refund to PROCESSING
        RefundRepository.update_refund_status(
            refund=refund,
            new_status=RefundStatus.PROCESSING,
            ledger_action=RefundLedgerAction.REFUND_PROCESSING,
        )

        payment = refund.payment

        # Execute refund via Gateway Adapter
        adapter = PaymentGatewayFactory.get_adapter(payment.gateway)
        gateway_res = adapter.refund(
            payment.gateway_transaction_id, float(refund.amount)
        )

        if gateway_res.get("success"):
            with transaction.atomic():
                # 1. Update Refund to SUCCESS
                RefundRepository.update_refund_status(
                    refund=refund,
                    new_status=RefundStatus.SUCCESS,
                    ledger_action=RefundLedgerAction.REFUND_SUCCESS,
                    gateway_refund_id=gateway_res.get(
                        "gateway_transaction_id", f"rfnd_gtw_{refund.refund_id}"
                    ),
                    gateway_response=gateway_res,
                )

                # 2. If Payment was WALLET method, credit customer wallet back!
                if payment.gateway == PaymentGateway.WALLET and payment.wallet:
                    WalletService.credit_wallet(
                        wallet_id=str(payment.wallet.id),
                        amount=refund.amount,
                        reference=refund.refund_id,
                        description=f"Refund for payment {payment.payment_id}",
                    )

                # 3. Update Payment Status (PARTIALLY_REFUNDED or FULLY_REFUNDED)
                total_refunded = RefundRepository.get_total_refunded_amount_for_payment(
                    payment
                )
                if total_refunded >= payment.amount:
                    payment.status = "FULLY_REFUNDED"
                else:
                    payment.status = "PARTIALLY_REFUNDED"
                payment.save(update_fields=["status", "updated_at"])

            logger.info(f"Refund '{refund_id_str}' processed successfully!")
            return True
        else:
            # Upstream Gateway Error -> Fail Refund
            error_msg = gateway_res.get("message", "Upstream gateway refund failure")
            RefundRepository.update_refund_status(
                refund=refund,
                new_status=RefundStatus.FAILED,
                ledger_action=RefundLedgerAction.REFUND_FAILED,
                failure_code="GATEWAY_REFUND_FAILED",
                failure_reason=error_msg,
                gateway_response=gateway_res,
            )
            return False

    except Exception as exc:
        logger.error(f"Error during refund processing for '{refund_id_str}': {exc}")
        if self.request.retries >= self.max_retries:
            # Max retries exceeded -> Mark FAILED & Move to Dead Letter Queue (DLQ)
            RefundRepository.update_refund_status(
                refund=refund,
                new_status=RefundStatus.FAILED,
                ledger_action=RefundLedgerAction.REFUND_FAILED,
                failure_code="MAX_RETRIES_EXCEEDED",
                failure_reason=str(exc),
            )
            RefundRepository.create_dlq_record(
                refund=refund,
                error_message=str(exc),
                retry_count=self.request.retries,
            )
            logger.critical(
                f"Refund '{refund_id_str}' permanently failed and moved to Dead Letter Queue (DLQ)."
            )
            return False
        raise self.retry(exc=exc, countdown=2**self.request.retries)
    finally:
        # Release Redis Distributed Lock
        cache.delete(lock_key)


@shared_task
def reconcile_refunds_task():
    """
    Celery Beat periodic task checking for un-reconciled PROCESSING refunds.
    """
    processing_refunds = Refund.objects.filter(status=RefundStatus.PROCESSING)
    reconciled_count = 0

    for refund in processing_refunds:
        # Retry task dispatch for stuck processing refunds
        process_refund_task.delay(refund.refund_id)
        reconciled_count += 1

    if reconciled_count > 0:
        logger.info(f"Reconciled {reconciled_count} processing refunds.")
    return reconciled_count
