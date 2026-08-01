import hashlib
from functools import wraps

from common.response import APIResponse
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response


def idempotency_key_required(timeout: int = 86400):
    """
    Decorator enforcing Idempotency-Key header processing with Redis caching.
    Prevents duplicate payment charging and duplicate refunds.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(view_instance, request, *args, **kwargs):
            idempotency_key = request.META.get("HTTP_IDEMPOTENCY_KEY")
            if not idempotency_key:
                # If key not provided, proceed without idempotency wrapper
                return view_func(view_instance, request, *args, **kwargs)

            # Compute request fingerprint
            body_str = request.body.decode("utf-8") if request.body else ""
            req_hash = hashlib.sha256(
                f"{request.path}:{body_str}".encode("utf-8")
            ).hexdigest()

            cache_key = f"idempotency:{idempotency_key}"
            cached_entry = cache.get(cache_key)

            if cached_entry:
                if cached_entry.get("status") == "PROCESSING":
                    return APIResponse.error(
                        message="A request with this Idempotency-Key is currently being processed.",
                        code="IDEMPOTENCY_PROCESSING",
                        status_code=status.HTTP_409_CONFLICT,
                    )
                if cached_entry.get("req_hash") != req_hash:
                    return APIResponse.error(
                        message="Idempotency-Key reused with different request payload.",
                        code="IDEMPOTENCY_KEY_MISMATCH",
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    )

                # Return cached response payload and HTTP status code
                return Response(
                    data=cached_entry["response_data"],
                    status=cached_entry["status_code"],
                )

            # Lock key during execution
            cache.set(
                cache_key,
                {"status": "PROCESSING", "req_hash": req_hash},
                timeout=30,
            )

            # Execute view function
            response = view_func(view_instance, request, *args, **kwargs)

            # Cache final response if HTTP status < 500
            if response.status_code < 500:
                cache.set(
                    cache_key,
                    {
                        "status": "COMPLETED",
                        "req_hash": req_hash,
                        "response_data": response.data,
                        "status_code": response.status_code,
                    },
                    timeout=timeout,
                )
            else:
                cache.delete(cache_key)

            return response

        return _wrapped_view

    return decorator
