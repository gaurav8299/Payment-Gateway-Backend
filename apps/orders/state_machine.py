from common.exceptions import BusinessLogicError
from orders.models import OrderStatus

VALID_TRANSITIONS = {
    OrderStatus.DRAFT: {OrderStatus.PENDING, OrderStatus.CANCELLED},
    OrderStatus.PENDING: {
        OrderStatus.PROCESSING,
        OrderStatus.PAID,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    },
    OrderStatus.PROCESSING: {
        OrderStatus.PAID,
        OrderStatus.FAILED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PAID: {OrderStatus.REFUNDED},
    OrderStatus.FAILED: {OrderStatus.PENDING, OrderStatus.CANCELLED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.REFUNDED: set(),
}


def validate_order_status_transition(current_status: str, target_status: str):
    """
    Validates if transitioning from current_status to target_status is permitted.
    """
    if current_status == target_status:
        return True

    allowed = VALID_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise BusinessLogicError(
            detail=f"Invalid order status transition from '{current_status}' to '{target_status}'. Allowed transitions: {list(allowed)}",
            code="INVALID_STATE_TRANSITION",
        )
    return True
