from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict

from accounts.models import User
from common.exceptions import BusinessLogicError, ResourceNotFoundError
from common.utils import generate_unique_id
from customer.repositories.customer_repository import CustomerRepository
from django.utils import timezone
from merchant.services.merchant_service import MerchantService
from orders.models import Order, OrderStatus
from orders.repositories.order_repository import OrderRepository
from orders.state_machine import validate_order_status_transition


class OrderService:
    """
    Business logic layer for Order creation, state machine transitions, and cancellation.
    """

    @classmethod
    def create_order(cls, user: User, validated_data: Dict[str, Any]) -> Order:
        merchant = MerchantService.get_or_create_profile(user)
        amount = Decimal(str(validated_data["amount"]))

        if amount <= 0:
            raise BusinessLogicError(
                detail="Order amount must be greater than 0.", code="INVALID_AMOUNT"
            )

        customer = None
        if validated_data.get("customer_id"):
            customer = CustomerRepository.get_by_id(
                validated_data["customer_id"], merchant
            )
            if not customer:
                raise ResourceNotFoundError(detail="Associated customer not found.")

        order_number = generate_unique_id("ord", length=24)
        expires_at = validated_data.get("expires_at")
        if not expires_at:
            expires_at = timezone.now() + timedelta(minutes=30)

        order = OrderRepository.create_order(
            order_number=order_number,
            merchant=merchant,
            customer=customer,
            amount=amount,
            currency=validated_data.get("currency", merchant.currency),
            description=validated_data.get("description", ""),
            metadata=validated_data.get("metadata", {}),
            status=validated_data.get("status", OrderStatus.PENDING),
            expires_at=expires_at,
            created_by=user.email,
        )

        return order

    @classmethod
    def get_order(cls, user: User, order_identifier: str) -> Order:
        merchant = MerchantService.get_or_create_profile(user)
        order = OrderRepository.get_by_order_number(order_identifier, merchant)
        if not order:
            order = OrderRepository.get_by_id(order_identifier, merchant)
        if not order:
            raise ResourceNotFoundError(detail="Order not found.")
        return order

    @classmethod
    def cancel_order(cls, user: User, order_identifier: str) -> Order:
        order = cls.get_order(user, order_identifier)
        validate_order_status_transition(order.status, OrderStatus.CANCELLED)
        return OrderRepository.update_order_status(
            order, OrderStatus.CANCELLED, updated_by=user.email
        )

    @classmethod
    def expire_order(cls, user: User, order_identifier: str) -> Order:
        order = cls.get_order(user, order_identifier)
        validate_order_status_transition(order.status, OrderStatus.EXPIRED)
        return OrderRepository.update_order_status(
            order, OrderStatus.EXPIRED, updated_by=user.email
        )
