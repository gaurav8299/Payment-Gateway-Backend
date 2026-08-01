from audit_logs.models import AuditLog
from audit_logs.serializers import AuditLogSerializer
from common.pagination import StandardResultsSetPagination
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List & Filter Audit Logs",
        description="Returns paginated, searchable, and filtered audit log traces.",
        parameters=[
            OpenApiParameter(
                name="actor_id",
                description="Filter by Actor ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="event_type",
                description="Filter by Event Type",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="resource_type",
                description="Filter by Resource Type",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="request_id",
                description="Filter by Request Correlation ID",
                required=False,
                type=str,
            ),
        ],
        responses={200: AuditLogSerializer(many=True)},
    )
    def get(self, request):
        qs = AuditLog.objects.all()

        actor_id = request.query_params.get("actor_id")
        event_type = request.query_params.get("event_type")
        resource_type = request.query_params.get("resource_type")
        request_id = request.query_params.get("request_id")

        if actor_id:
            qs = qs.filter(actor_id=actor_id)
        if event_type:
            qs = qs.filter(event_type=event_type)
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        if request_id:
            qs = qs.filter(request_id=request_id)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = AuditLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
