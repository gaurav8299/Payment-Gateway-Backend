from audit_logs.models import AuditLog
from django.contrib import admin


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "audit_id",
        "event_type",
        "actor_type",
        "actor_id",
        "resource_type",
        "http_method",
        "status_code",
        "created_at",
    )
    list_filter = ("event_type", "actor_type", "http_method", "status_code")
    search_fields = ("audit_id", "actor_id", "resource_id", "request_id", "endpoint")
