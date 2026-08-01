from common.decorators.idempotency import idempotency_key_required
from common.pagination import StandardResultsSetPagination
from common.response import APIResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from merchant.services.merchant_service import MerchantService
from refunds.repositories.refund_repository import RefundRepository
from refunds.serializers import (
    RefundCreateSerializer,
    RefundLedgerSerializer,
    RefundSerializer,
)
from refunds.services.refund_service import RefundService
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


class RefundListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "refunds"

    @extend_schema(
        summary="List & Filter Refunds",
        description="Returns paginated refunds for merchant filtered by status, payment_id, or search term.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by Refund Status",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="payment_id",
                description="Filter by Payment ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="search",
                description="Search by refund_id or gateway_refund_id",
                required=False,
                type=str,
            ),
        ],
        responses={200: RefundSerializer(many=True)},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        status_param = request.query_params.get("status")
        payment_id = request.query_params.get("payment_id")
        search = request.query_params.get("search")

        queryset = RefundRepository.list_refunds_queryset(
            merchant=merchant,
            payment_id=payment_id,
            status=status_param,
            search_query=search,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = RefundSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Request Payment Refund",
        description="Submits asynchronous payment refund request. Dispatches Celery processing task. Supports Idempotency-Key header.",
        request=RefundCreateSerializer,
        responses={201: RefundSerializer},
    )
    @idempotency_key_required(timeout=86400)
    def post(self, request):
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refund = RefundService.create_refund(request.user, serializer.validated_data)
        return APIResponse.success(
            data=RefundSerializer(refund).data,
            message="Refund request created and queued for processing.",
            status_code=status.HTTP_201_CREATED,
        )


class RefundDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Refund Details",
        description="Returns details of a refund by UUID or refund_id (`rfnd_...`).",
        responses={200: RefundSerializer},
    )
    def get(self, request, refund_id):
        refund = RefundService.get_refund(request.user, refund_id)
        return APIResponse.success(
            data=RefundSerializer(refund).data,
            message="Refund details retrieved successfully.",
        )


class RefundLedgerView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Refund Audit Ledger",
        description="Returns immutable financial ledger entries for a refund.",
        responses={200: RefundLedgerSerializer(many=True)},
    )
    def get(self, request, refund_id):
        refund = RefundService.get_refund(request.user, refund_id)
        ledger_entries = refund.ledger_entries.all()
        serializer = RefundLedgerSerializer(ledger_entries, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="Refund audit ledger retrieved successfully.",
        )


class RefundMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Refund Operational Metrics",
        description="Exposes merchant refund statistics (total requested, success rate %, total refunded amount, DLQ records).",
        responses={200: dict},
    )
    def get(self, request):
        metrics = RefundService.get_refund_metrics(request.user)
        return APIResponse.success(
            data=metrics,
            message="Refund metrics generated successfully.",
        )
