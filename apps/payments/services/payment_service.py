from decimal import Decimal
from typing import Any, Dict

from accounts.models import User
from common.exceptions import BusinessLogicError, ResourceNotFoundError
from common.utils import generate_unique_id
from django.db import transaction
from merchant.services.merchant_service import MerchantService
from orders.models import OrderStatus
from orders.repositories.order_repository import OrderRepository
from orders.services.order_service import OrderService
from payments.factories import PaymentGatewayFactory
from payments.models import (
    Payment,
    PaymentGateway,
    PaymentLedgerAction,
    PaymentMethod,
    PaymentStatus,
)
from payments.repositories.payment_repository import PaymentRepository
from payments.state_machine import validate_payment_status_transition


class PaymentService:
    """
    Business logic layer for Payment creation, Gateway delegation, and state synchronization.
    """

    @classmethod
    def create_payment(cls, user: User, validated_data: Dict[str, Any]) -> Payment:
        merchant = MerchantService.get_or_create_profile(user)
        order_identifier = validated_data["order_id"]
        order = OrderService.get_order(user, order_identifier)

        if order.status not in [
            OrderStatus.PENDING,
            OrderStatus.PROCESSING,
            OrderStatus.DRAFT,
        ]:
            raise BusinessLogicError(
                detail=f"Cannot create payment for order in '{order.status}' status.",
                code="INVALID_ORDER_STATUS",
            )

        amount = Decimal(str(validated_data.get("amount", order.amount)))
        if amount != order.amount:
            raise BusinessLogicError(
                detail=f"Payment amount ({amount}) does not match Order amount ({order.amount}).",
                code="AMOUNT_MISMATCH",
            )

        gateway_type = validated_data.get("gateway", PaymentGateway.DUMMY)
        payment_method = validated_data.get("payment_method", PaymentMethod.CARD)
        payment_id_str = generate_unique_id("pay", length=24)

        # Get Gateway Adapter from Factory
        adapter = PaymentGatewayFactory.get_adapter(gateway_type)

        # Dispatch payment creation to adapter
        gateway_res = adapter.create_payment(
            payment_id=payment_id_str,
            amount=float(amount),
            currency=order.currency,
            payment_method=payment_method,
            metadata=validated_data.get("metadata", {}),
        )

        # Retrieve wallet entity if wallet_id provided in metadata
        wallet_obj = None
        metadata = validated_data.get("metadata", {})
        if metadata.get("wallet_id"):
            from wallet.repositories.wallet_repository import WalletRepository

            wallet_obj = WalletRepository.get_by_id(metadata["wallet_id"])

        with transaction.atomic():
            payment_status = PaymentStatus.CREATED
            if gateway_res.get("success"):
                if gateway_res.get("status") == "CAPTURED":
                    payment_status = PaymentStatus.CAPTURED
                elif gateway_res.get("status") == "AUTHORIZED":
                    payment_status = PaymentStatus.AUTHORIZED
            else:
                payment_status = PaymentStatus.FAILED

            payment = PaymentRepository.create_payment(
                payment_id_str=payment_id_str,
                order=order,
                merchant=merchant,
                customer=order.customer,
                wallet=wallet_obj,
                amount=amount,
                currency=order.currency,
                payment_method=payment_method,
                gateway=gateway_type,
                gateway_transaction_id=gateway_res.get("gateway_transaction_id", ""),
                status=payment_status,
                metadata=metadata,
            )

            # Synchronize Order Status
            if payment_status == PaymentStatus.CAPTURED:
                OrderRepository.update_order_status(
                    order, OrderStatus.PAID, updated_by=user.email
                )
            elif payment_status == PaymentStatus.AUTHORIZED:
                OrderRepository.update_order_status(
                    order, OrderStatus.PROCESSING, updated_by=user.email
                )
            elif payment_status == PaymentStatus.FAILED:
                payment.failure_code = gateway_res.get("failure_code", "PAYMENT_FAILED")
                payment.failure_reason = gateway_res.get(
                    "failure_reason", "Payment failed on upstream gateway"
                )
                payment.save(update_fields=["failure_code", "failure_reason"])

            return payment

    @classmethod
    def capture_payment(cls, user: User, payment_id_str: str) -> Payment:
        merchant = MerchantService.get_or_create_profile(user)
        payment = PaymentRepository.get_by_payment_id_str(payment_id_str, merchant)
        if not payment:
            payment = PaymentRepository.get_by_id(payment_id_str, merchant)
        if not payment:
            raise ResourceNotFoundError(detail="Payment not found.")

        validate_payment_status_transition(payment.status, PaymentStatus.CAPTURED)

        adapter = PaymentGatewayFactory.get_adapter(payment.gateway)
        gateway_res = adapter.capture(
            payment.gateway_transaction_id, float(payment.amount)
        )

        if not gateway_res.get("success"):
            raise BusinessLogicError(
                detail=f"Gateway capture failed: {gateway_res.get('message')}"
            )

        with transaction.atomic():
            payment = PaymentRepository.update_payment_status(
                payment=payment,
                new_status=PaymentStatus.CAPTURED,
                ledger_action=PaymentLedgerAction.PAYMENT_CAPTURED,
                gateway_response=gateway_res,
            )
            # Update order to PAID
            OrderRepository.update_order_status(
                payment.order, OrderStatus.PAID, updated_by=user.email
            )

        return payment

    @classmethod
    def void_payment(cls, user: User, payment_id_str: str) -> Payment:
        merchant = MerchantService.get_or_create_profile(user)
        payment = PaymentRepository.get_by_payment_id_str(payment_id_str, merchant)
        if not payment:
            payment = PaymentRepository.get_by_id(payment_id_str, merchant)
        if not payment:
            raise ResourceNotFoundError(detail="Payment not found.")

        validate_payment_status_transition(payment.status, PaymentStatus.VOIDED)

        adapter = PaymentGatewayFactory.get_adapter(payment.gateway)
        gateway_res = adapter.void(payment.gateway_transaction_id)

        with transaction.atomic():
            payment = PaymentRepository.update_payment_status(
                payment=payment,
                new_status=PaymentStatus.VOIDED,
                ledger_action=PaymentLedgerAction.PAYMENT_VOIDED,
                gateway_response=gateway_res,
            )
            OrderRepository.update_order_status(
                payment.order, OrderStatus.CANCELLED, updated_by=user.email
            )

        return payment

    @classmethod
    def get_payment(cls, user: User, payment_id_str: str) -> Payment:
        merchant = MerchantService.get_or_create_profile(user)
        payment = PaymentRepository.get_by_payment_id_str(payment_id_str, merchant)
        if not payment:
            payment = PaymentRepository.get_by_id(payment_id_str, merchant)
        if not payment:
            raise ResourceNotFoundError(detail="Payment not found.")
        return payment
