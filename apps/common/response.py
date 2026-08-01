from common.middleware import get_current_correlation_id
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response


class APIResponse:
    """
    Standardized API Response Builder.
    """

    @staticmethod
    def success(
        data=None,
        message="Operation successful",
        status_code=status.HTTP_200_OK,
        meta=None,
    ):
        payload = {
            "success": True,
            "message": message,
            "data": data if data is not None else {},
            "timestamp": timezone.now().isoformat(),
            "correlation_id": get_current_correlation_id(),
        }
        if meta:
            payload["meta"] = meta
        return Response(payload, status=status_code)

    @staticmethod
    def error(
        message="Operation failed",
        code="BAD_REQUEST",
        details=None,
        status_code=status.HTTP_400_BAD_REQUEST,
    ):
        payload = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "timestamp": timezone.now().isoformat(),
            },
            "correlation_id": get_current_correlation_id(),
        }
        return Response(payload, status=status_code)
