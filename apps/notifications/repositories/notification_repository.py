from typing import Optional

from django.db.models import QuerySet
from notifications.models import Notification


class NotificationRepository:
    """
    Repository class providing data access routines for Notification logs.
    """

    @staticmethod
    def get_by_id(notification_id: str) -> Optional[Notification]:
        try:
            return Notification.objects.get(notification_id=notification_id)
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def list_notifications(
        recipient: Optional[str] = None, status: Optional[str] = None
    ) -> QuerySet:
        qs = Notification.objects.all()
        if recipient:
            qs = qs.filter(recipient=recipient)
        if status:
            qs = qs.filter(status=status)
        return qs
