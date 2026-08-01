from notifications.models import Notification
from rest_framework import serializers


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_id",
            "recipient",
            "recipient_type",
            "channel",
            "subject",
            "template_name",
            "payload",
            "status",
            "retry_count",
            "scheduled_at",
            "sent_at",
            "failure_reason",
            "created_at",
        ]
        read_only_fields = fields
