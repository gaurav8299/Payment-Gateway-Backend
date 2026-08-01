import json

from audit_logs.models import AuditActorType
from audit_logs.services.audit_service import AuditService
from django.utils.deprecation import MiddlewareMixin


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware automatically recording sanitized audit log traces for mutating API requests (POST, PUT, PATCH, DELETE).
    """

    EXCLUDED_PATHS = ["/api/v1/schema/", "/api/v1/health/"]

    def process_response(self, request, response):
        path = request.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return response

        # Only audit mutating methods or errors
        if (
            request.method not in ["POST", "PUT", "PATCH", "DELETE"]
            and response.status_code < 400
        ):
            return response

        actor_type = AuditActorType.SYSTEM
        actor_id = ""

        if hasattr(request, "user") and request.user.is_authenticated:
            user = request.user
            actor_id = str(user.id)
            if hasattr(user, "role"):
                actor_type = user.role
            else:
                actor_type = AuditActorType.MERCHANT

        ip_address = request.META.get("HTTP_X_FORWARDED_FOR")
        if ip_address:
            ip_address = ip_address.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")

        req_payload = {}
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                if request.content_type == "application/json" and request.body:
                    req_payload = json.loads(request.body.decode("utf-8"))
            except Exception:
                pass

        resp_payload = {}
        try:
            if hasattr(response, "data"):
                resp_payload = response.data
        except Exception:
            pass

        AuditService.log(
            {
                "event_type": f"api.{request.method.lower()}",
                "actor_type": actor_type,
                "actor_id": actor_id,
                "resource_type": "api_endpoint",
                "resource_id": path,
                "http_method": request.method,
                "endpoint": path,
                "request_id": getattr(request, "correlation_id", ""),
                "ip_address": ip_address,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
                "status_code": response.status_code,
                "action": f"{request.method} {path}",
                "request_payload": req_payload,
                "response_payload": resp_payload,
            }
        )

        return response
