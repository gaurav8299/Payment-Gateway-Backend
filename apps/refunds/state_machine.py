from common.exceptions import BusinessLogicError
from refunds.models import RefundStatus

VALID_REFUND_TRANSITIONS = {
    RefundStatus.CREATED: {RefundStatus.PROCESSING},
    RefundStatus.PROCESSING: {RefundStatus.SUCCESS, RefundStatus.FAILED},
    RefundStatus.SUCCESS: set(),
    RefundStatus.FAILED: set(),
}


def validate_refund_status_transition(current_status: str, target_status: str):
    """
    Validates if transitioning from current_status to target_status is permitted.
    """
    if current_status == target_status:
        return True

    allowed = VALID_REFUND_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise BusinessLogicError(
            detail=f"Invalid refund status transition from '{current_status}' to '{target_status}'. Allowed transitions: {list(allowed)}",
            code="INVALID_STATE_TRANSITION",
        )
    return True
