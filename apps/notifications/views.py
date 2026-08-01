from common.exceptions import ResourceNotFoundError
from common.pagination import StandardResultsSetPagination
from common.response import APIResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from notifications.tasks import send_notification_task
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List Notifications",
        description="Returns paginated notification history.",
        parameters=[
            OpenApiParameter(
                name="recipient",
                description="Filter by recipient email",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="status", description="Filter by status", required=False, type=str
            ),
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        qs = Notification.objects.all()

        recipient = request.query_params.get("recipient")
        status_param = request.query_params.get("status")

        if recipient:
            qs = qs.filter(recipient=recipient)
        if status_param:
            qs = qs.filter(status=status_param)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class NotificationRetryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Retry Failed Notification",
        description="Re-dispatches an async email notification task.",
        responses={200: NotificationSerializer},
    )
    def post(self, request, notification_id):
        try:
            notif = Notification.objects.get(notification_id=notification_id)
        except Notification.DoesNotExist:
            raise ResourceNotFoundError(detail="Notification not found.")

        send_notification_task.delay(notif.notification_id)
        return APIResponse.success(
            data=NotificationSerializer(notif).data,
            message="Notification retry task queued successfully.",
        )
