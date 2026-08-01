import logging

from common.middleware import get_current_correlation_id
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("payment_gateway")


class BaseCustomException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "BAD_REQUEST"
    default_detail = "A business logic error occurred."

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        self.code = code
        super().__init__(detail=detail, code=code)


class BusinessLogicError(BaseCustomException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "BUSINESS_LOGIC_ERROR"
    default_detail = "Invalid business operation."


class ResourceNotFoundError(BaseCustomException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "RESOURCE_NOT_FOUND"
    default_detail = "Requested resource was not found."


class IdempotencyError(BaseCustomException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "IDEMPOTENCY_CONFLICT"
    default_detail = "Duplicate request detected with conflicting idempotency key."


class PaymentGatewayError(BaseCustomException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "PAYMENT_GATEWAY_ERROR"
    default_detail = "Upstream payment processor error."


class InsufficientWalletBalanceError(BaseCustomException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "INSUFFICIENT_WALLET_BALANCE"
    default_detail = "Wallet balance is insufficient to complete transaction."


def custom_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework providing consistent API error outputs.
    """
    response = exception_handler(exc, context)
    correlation_id = get_current_correlation_id()

    if response is not None:
        error_code = getattr(exc, "code", getattr(exc, "default_code", "API_ERROR"))
        if isinstance(exc, ValidationError):
            error_code = "VALIDATION_ERROR"

        error_message = "An error occurred while processing your request."
        if hasattr(exc, "detail"):
            if isinstance(exc.detail, str):
                error_message = exc.detail
            elif isinstance(exc.detail, list) and exc.detail:
                error_message = str(exc.detail[0])
            elif isinstance(exc.detail, dict):
                error_message = "Validation error."

        custom_response_data = {
            "success": False,
            "error": {
                "code": str(error_code).upper(),
                "message": error_message,
                "details": response.data,
                "timestamp": timezone.now().isoformat(),
            },
            "correlation_id": correlation_id,
        }
        response.data = custom_response_data
    else:
        # Unhandled Python Exception (500 Internal Server Error)
        logger.exception(f"Unhandled Server Error: {exc}")
        custom_response_data = {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
                "details": None,
                "timestamp": timezone.now().isoformat(),
            },
            "correlation_id": correlation_id,
        }
        response = Response(
            data=custom_response_data,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
