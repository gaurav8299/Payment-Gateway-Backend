from typing import Any, Dict

from audit_logs.backends.db_backend import DatabaseAuditBackend
from audit_logs.backends.file_backend import FileAuditBackend
from audit_logs.sanitizer import sanitize_payload


class AuditService:
    """
    Central Service layer for recording sanitized audit entries across pluggable backends.
    """

    _backends = [DatabaseAuditBackend(), FileAuditBackend()]

    @classmethod
    def log(cls, audit_data: Dict[str, Any]) -> None:
        # Sanitize payloads before sending to storage backends
        sanitized_data = {
            "event_type": audit_data.get("event_type", "api.request"),
            "actor_type": audit_data.get("actor_type", "SYSTEM"),
            "actor_id": str(audit_data.get("actor_id", "")),
            "resource_type": audit_data.get("resource_type", "system"),
            "resource_id": str(audit_data.get("resource_id", "none")),
            "http_method": audit_data.get("http_method", ""),
            "endpoint": audit_data.get("endpoint", ""),
            "request_id": audit_data.get("request_id", ""),
            "ip_address": audit_data.get("ip_address"),
            "user_agent": audit_data.get("user_agent", ""),
            "status_code": audit_data.get("status_code"),
            "action": audit_data.get("action", "exec"),
            "request_payload": sanitize_payload(audit_data.get("request_payload", {})),
            "response_payload": sanitize_payload(
                audit_data.get("response_payload", {})
            ),
            "metadata": sanitize_payload(audit_data.get("metadata", {})),
        }

        for backend in cls._backends:
            try:
                backend.log(sanitized_data)
            except Exception:
                pass
