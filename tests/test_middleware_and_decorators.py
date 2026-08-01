import json

import pytest
from audit_logs.middleware import AuditLoggingMiddleware
from common.decorators.idempotency import idempotency_key_required
from common.middleware import CorrelationIDMiddleware
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from rest_framework import status
from rest_framework.response import Response


@pytest.mark.django_db
class TestMiddlewareAndDecorators:
    def test_correlation_id_middleware(self):
        rf = RequestFactory()
        request = rf.get("/api/v1/health/")

        # Test request without correlation ID header
        middleware = CorrelationIDMiddleware(lambda req: Response({"status": "ok"}))
        response = middleware(request)
        assert "X-Correlation-ID" in response
        assert response["X-Correlation-ID"] is not None

        # Test request with correlation ID header
        request_with_id = rf.get(
            "/api/v1/health/", HTTP_X_CORRELATION_ID="custom-corr-id-999"
        )
        response_custom = middleware(request_with_id)
        assert response_custom["X-Correlation-ID"] == "custom-corr-id-999"

    def test_idempotent_request_decorator_caching(self):
        rf = RequestFactory()

        @idempotency_key_required(timeout=300)
        def dummy_view(self_or_inst, request):
            return Response(
                {"message": "Processed successfully", "value": 123},
                status=status.HTTP_200_OK,
            )

        # 1. Request without Idempotency-Key -> executed directly
        req1 = rf.post(
            "/api/v1/payments/",
            data=json.dumps({"amount": 100}),
            content_type="application/json",
        )
        res1 = dummy_view(None, req1)
        assert res1.status_code == status.HTTP_200_OK

        # 2. First Request with Idempotency-Key -> processed and cached
        req2 = rf.post(
            "/api/v1/payments/",
            data=json.dumps({"amount": 100}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="idem-key-abc-123",
        )
        res2 = dummy_view(None, req2)
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["message"] == "Processed successfully"

        # 3. Duplicate Request with SAME Idempotency-Key -> returned from cache!
        req3 = rf.post(
            "/api/v1/payments/",
            data=json.dumps({"amount": 100}),
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="idem-key-abc-123",
        )
        res3 = dummy_view(None, req3)
        assert res3.status_code == status.HTTP_200_OK
        assert res3.data["message"] == "Processed successfully"

    def test_audit_logging_middleware(self):
        rf = RequestFactory()
        request = rf.post(
            "/api/v1/accounts/login/",
            data=json.dumps(
                {"email": "test@example.com", "password": "SecretPassword123!"}
            ),
            content_type="application/json",
        )
        request.user = AnonymousUser()

        middleware = AuditLoggingMiddleware(
            get_response=lambda req: Response({"success": True}, status=200)
        )
        response = middleware(request)
        assert response.status_code == 200
