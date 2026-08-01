from django.contrib import admin
from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "notification_id",
        "recipient",
        "channel",
        "subject",
        "status",
        "retry_count",
        "sent_at",
        "created_at",
    )
    list_filter = ("channel", "status", "recipient_type")
    search_fields = ("notification_id", "recipient", "subject")
