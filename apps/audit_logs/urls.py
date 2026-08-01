from audit_logs.views import AuditLogListView
from django.urls import path

app_name = "audit_logs"

urlpatterns = [
    path("", AuditLogListView.as_view(), name="audit_log_list"),
]
