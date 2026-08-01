from typing import Optional
from uuid import UUID

from customer.models import CustomerProfile
from django.db.models import Q, QuerySet
from merchant.models import MerchantProfile
from orders.models import Order, OrderEvent, OrderEventType, OrderStatus


class OrderRepository:
    """
    Repository class providing data access operations for Order domain.
    """

    @staticmethod
    def get_by_id(
        order_id: UUID | str, merchant: Optional[MerchantProfile] = None
    ) -> Optional[Order]:
        try:
            qs = Order.objects.all()
            if merchant:
                qs = qs.filter(merchant=merchant)
            return qs.get(id=order_id)
        except Order.DoesNotExist:
            return None

    @staticmethod
    def get_by_order_number(
        order_number: str, merchant: Optional[MerchantProfile] = None
    ) -> Optional[Order]:
        try:
            qs = Order.objects.all()
            if merchant:
                qs = qs.filter(merchant=merchant)
            return qs.get(order_number=order_number)
        except Order.DoesNotExist:
            return None

    @staticmethod
    def create_order(
        order_number: str,
        merchant: MerchantProfile,
        amount,
        currency: str = "INR",
        customer: Optional[CustomerProfile] = None,
        description: str = "",
        metadata: Optional[dict] = None,
        status: str = OrderStatus.PENDING,
        expires_at=None,
        created_by: str = "",
    ) -> Order:
        order = Order.objects.create(
            order_number=order_number,
            merchant=merchant,
            customer=customer,
            amount=amount,
            currency=currency.upper(),
            description=description,
            metadata=metadata or {},
            status=status,
            expires_at=expires_at,
            created_by=created_by,
        )

        # Log Order Created Domain Event
        OrderEvent.objects.create(
            order=order,
            event_type=OrderEventType.CREATED,
            payload={
                "order_number": order.order_number,
                "amount": str(order.amount),
                "currency": order.currency,
                "status": order.status,
            },
        )
        return order

    @staticmethod
    def update_order_status(
        order: Order, new_status: str, updated_by: str = ""
    ) -> Order:
        order.status = new_status
        if updated_by:
            order.updated_by = updated_by
        order.save(update_fields=["status", "updated_by", "updated_at"])

        event_type = OrderEventType.UPDATED
        if new_status == OrderStatus.CANCELLED:
            event_type = OrderEventType.CANCELLED
        elif new_status == OrderStatus.EXPIRED:
            event_type = OrderEventType.EXPIRED
        elif new_status == OrderStatus.PAID:
            event_type = OrderEventType.PAID

        OrderEvent.objects.create(
            order=order,
            event_type=event_type,
            payload={"status": new_status, "updated_by": updated_by},
        )
        return order

    @staticmethod
    def list_orders_queryset(
        merchant: MerchantProfile,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> QuerySet:
        qs = Order.objects.filter(merchant=merchant)
        if status:
            qs = qs.filter(status=status)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if search_query:
            qs = qs.filter(
                Q(order_number__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(customer__email__icontains=search_query)
            )
        return qs
