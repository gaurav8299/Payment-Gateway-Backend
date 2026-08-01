from django.urls import path
from notifications.views import NotificationListView, NotificationRetryView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification_list"),
    path(
        "<str:notification_id>/retry/",
        NotificationRetryView.as_view(),
        name="notification_retry",
    ),
]
