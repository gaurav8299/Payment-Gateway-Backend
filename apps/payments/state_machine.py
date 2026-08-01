from common.exceptions import BusinessLogicError
from payments.models import PaymentStatus

VALID_PAYMENT_TRANSITIONS = {
    PaymentStatus.CREATED: {
        PaymentStatus.AUTHORIZED,
        PaymentStatus.CAPTURED,
        PaymentStatus.FAILED,
    },
    PaymentStatus.AUTHORIZED: {
        PaymentStatus.CAPTURED,
        PaymentStatus.VOIDED,
        PaymentStatus.FAILED,
    },
    PaymentStatus.CAPTURED: {PaymentStatus.SETTLED},
    PaymentStatus.SETTLED: set(),
    PaymentStatus.FAILED: set(),
    PaymentStatus.VOIDED: set(),
}


def validate_payment_status_transition(current_status: str, target_status: str):
    """
    Validates if transitioning from current_status to target_status is permitted.
    """
    if current_status == target_status:
        return True

    allowed = VALID_PAYMENT_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise BusinessLogicError(
            detail=f"Invalid payment status transition from '{current_status}' to '{target_status}'. Allowed transitions: {list(allowed)}",
            code="INVALID_STATE_TRANSITION",
        )
    return True
