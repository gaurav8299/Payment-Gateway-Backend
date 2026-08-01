from typing import Any, Dict

from audit_logs.backends.base import BaseAuditBackend
from audit_logs.models import AuditLog
from common.utils import generate_unique_id


class DatabaseAuditBackend(BaseAuditBackend):
    """
    Audit logging backend storing audit traces in the PostgreSQL relational database.
    """

    def log(self, audit_data: Dict[str, Any]) -> None:
        audit_id_str = generate_unique_id("aud", length=24)
        AuditLog.objects.create(
            audit_id=audit_id_str,
            event_type=audit_data.get("event_type", "api.request"),
            actor_type=audit_data.get("actor_type", "SYSTEM"),
            actor_id=audit_data.get("actor_id", ""),
            resource_type=audit_data.get("resource_type", "system"),
            resource_id=audit_data.get("resource_id", "none"),
            http_method=audit_data.get("http_method", ""),
            endpoint=audit_data.get("endpoint", ""),
            request_id=audit_data.get("request_id", ""),
            ip_address=audit_data.get("ip_address"),
            user_agent=audit_data.get("user_agent", ""),
            status_code=audit_data.get("status_code"),
            action=audit_data.get("action", "exec"),
            request_payload=audit_data.get("request_payload", {}),
            response_payload=audit_data.get("response_payload", {}),
            metadata=audit_data.get("metadata", {}),
        )
