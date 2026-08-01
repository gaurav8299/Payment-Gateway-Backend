import logging
import threading
import uuid

from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()


def get_current_correlation_id():
    """
    Retrieve the correlation ID for the current thread context.
    """
    return getattr(_thread_locals, "correlation_id", "N/A")


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter that injects correlation_id into log records.
    """

    def filter(self, record):
        record.correlation_id = get_current_correlation_id()
        return True


class CorrelationIDMiddleware(MiddlewareMixin):
    """
    Middleware to handle request correlation IDs for distributed tracing.
    Exposes X-Correlation-ID on both request and response.
    """

    HEADER_NAME = "HTTP_X_CORRELATION_ID"
    RESPONSE_HEADER = "X-Correlation-ID"

    def process_request(self, request):
        correlation_id = request.META.get(self.HEADER_NAME)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        request.correlation_id = correlation_id
        _thread_locals.correlation_id = correlation_id

    def process_response(self, request, response):
        correlation_id = getattr(
            request, "correlation_id", get_current_correlation_id()
        )
        response[self.RESPONSE_HEADER] = correlation_id
        # Clean thread locals after request processing
        _thread_locals.correlation_id = "N/A"
        return response
