from common.decorators.idempotency import idempotency_key_required
from common.pagination import StandardResultsSetPagination
from common.response import APIResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from merchant.services.merchant_service import MerchantService
from payments.repositories.payment_repository import PaymentRepository
from payments.serializers import (
    PaymentCreateSerializer,
    PaymentLedgerSerializer,
    PaymentSerializer,
)
from payments.services.payment_service import PaymentService
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


class PaymentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payments"

    @extend_schema(
        summary="List & Filter Payments",
        description="Returns paginated list of payments filtered by status, gateway, or search term.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by Payment Status",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="gateway",
                description="Filter by Gateway",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="search",
                description="Search by payment_id or transaction_id",
                required=False,
                type=str,
            ),
        ],
        responses={200: PaymentSerializer(many=True)},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        status_param = request.query_params.get("status")
        gateway_param = request.query_params.get("gateway")
        search = request.query_params.get("search")

        queryset = PaymentRepository.list_payments_queryset(
            merchant=merchant,
            status=status_param,
            gateway=gateway_param,
            search_query=search,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PaymentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create Payment Intent / Charge",
        description="Executes a payment charge against an Order using selected Gateway Adapter (Dummy, Stripe, Razorpay, Wallet). Supports Idempotency-Key header.",
        request=PaymentCreateSerializer,
        responses={201: PaymentSerializer},
    )
    @idempotency_key_required(timeout=86400)
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = PaymentService.create_payment(request.user, serializer.validated_data)
        return APIResponse.success(
            data=PaymentSerializer(payment).data,
            message="Payment charge processed successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Payment Details",
        description="Returns full details of a payment by UUID or payment_id (`pay_...`).",
        responses={200: PaymentSerializer},
    )
    def get(self, request, payment_id):
        payment = PaymentService.get_payment(request.user, payment_id)
        return APIResponse.success(
            data=PaymentSerializer(payment).data,
            message="Payment details retrieved successfully.",
        )


class PaymentCaptureView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payments"

    @extend_schema(
        summary="Capture Authorized Payment",
        description="Captures an AUTHORIZED payment and updates Order status to PAID.",
        responses={200: PaymentSerializer},
    )
    @idempotency_key_required(timeout=86400)
    def post(self, request, payment_id):
        payment = PaymentService.capture_payment(request.user, payment_id)
        return APIResponse.success(
            data=PaymentSerializer(payment).data,
            message="Payment captured successfully.",
        )


class PaymentVoidView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payments"

    @extend_schema(
        summary="Void Authorized Payment",
        description="Voids an AUTHORIZED payment and cancels Order.",
        responses={200: PaymentSerializer},
    )
    @idempotency_key_required(timeout=86400)
    def post(self, request, payment_id):
        payment = PaymentService.void_payment(request.user, payment_id)
        return APIResponse.success(
            data=PaymentSerializer(payment).data,
            message="Payment voided successfully.",
        )


class PaymentLedgerView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Payment Financial Audit Ledger",
        description="Returns immutable financial ledger entries for a payment.",
        responses={200: PaymentLedgerSerializer(many=True)},
    )
    def get(self, request, payment_id):
        payment = PaymentService.get_payment(request.user, payment_id)
        ledger_entries = payment.ledger_entries.all()
        serializer = PaymentLedgerSerializer(ledger_entries, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="Payment audit ledger retrieved successfully.",
        )
