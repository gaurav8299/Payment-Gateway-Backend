from audit_logs.models import AuditLog
from rest_framework import serializers


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "audit_id",
            "event_type",
            "actor_type",
            "actor_id",
            "resource_type",
            "resource_id",
            "http_method",
            "endpoint",
            "request_id",
            "ip_address",
            "user_agent",
            "status_code",
            "action",
            "request_payload",
            "response_payload",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
