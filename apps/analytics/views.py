from analytics.serializers import (
    ChartFilterSerializer,
    CouponCreateSerializer,
    CouponSerializer,
    CouponValidateSerializer,
    InvoiceSerializer,
    MerchantReportFilterSerializer,
)
from analytics.services import AnalyticsService
from analytics.services.coupon_service import CouponService
from analytics.services.export_service import ExportService
from analytics.services.invoice_service import InvoiceService
from common.exceptions import ResourceNotFoundError
from common.pagination import StandardResultsSetPagination
from common.response import APIResponse
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


# ──────────────────────────────────────────────────────────
# MERCHANT DASHBOARD
# ──────────────────────────────────────────────────────────
class MerchantDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Merchant Dashboard Metrics",
        description="Returns aggregated revenue, payment, and refund KPIs for a merchant.",
        parameters=[
            OpenApiParameter(
                name="merchant_id", description="Merchant UUID", required=True, type=str
            ),
        ],
    )
    def get(self, request):
        merchant_id = request.query_params.get("merchant_id")
        if not merchant_id:
            return APIResponse.error(
                message="merchant_id is required.", status_code=400
            )

        data = AnalyticsService.get_merchant_dashboard(merchant_id)
        return APIResponse.success(
            data=data, message="Merchant dashboard metrics retrieved."
        )


# ──────────────────────────────────────────────────────────
# CHART DATA
# ──────────────────────────────────────────────────────────
class ChartDataView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Chart Data for Merchant",
        description="Returns time-series chart data (revenue, refund, payment method, status distribution).",
        parameters=[
            OpenApiParameter(name="merchant_id", required=True, type=str),
            OpenApiParameter(name="granularity", required=False, type=str),
            OpenApiParameter(name="days", required=False, type=int),
        ],
    )
    def get(self, request):
        merchant_id = request.query_params.get("merchant_id")
        if not merchant_id:
            return APIResponse.error(
                message="merchant_id is required.", status_code=400
            )

        serializer = ChartFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        granularity = serializer.validated_data.get("granularity", "daily")
        days = serializer.validated_data.get("days", 30)

        data = AnalyticsService.get_chart_data(merchant_id, granularity, days)
        return APIResponse.success(data=data, message="Chart data retrieved.")


# ──────────────────────────────────────────────────────────
# SETTLEMENT REPORT
# ──────────────────────────────────────────────────────────
class SettlementReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Settlement Report",
        description="Returns settlement summary (captured, settled, pending, refunded).",
        parameters=[
            OpenApiParameter(name="merchant_id", required=True, type=str),
        ],
    )
    def get(self, request):
        merchant_id = request.query_params.get("merchant_id")
        if not merchant_id:
            return APIResponse.error(
                message="merchant_id is required.", status_code=400
            )

        data = AnalyticsService.get_settlement_report(merchant_id)
        return APIResponse.success(data=data, message="Settlement report retrieved.")


# ──────────────────────────────────────────────────────────
# MERCHANT REPORTS (with export)
# ──────────────────────────────────────────────────────────
class MerchantReportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Merchant Reports (Revenue, Refund, Order, Wallet, Transaction)",
        description="Generate filterable reports with optional CSV/JSON export.",
        parameters=[
            OpenApiParameter(name="merchant_id", required=True, type=str),
            OpenApiParameter(name="report_type", required=False, type=str),
            OpenApiParameter(name="date_from", required=False, type=str),
            OpenApiParameter(name="date_to", required=False, type=str),
            OpenApiParameter(name="status", required=False, type=str),
            OpenApiParameter(name="currency", required=False, type=str),
            OpenApiParameter(name="payment_method", required=False, type=str),
            OpenApiParameter(name="gateway", required=False, type=str),
            OpenApiParameter(name="export_format", required=False, type=str),
        ],
    )
    def get(self, request):
        merchant_id = request.query_params.get("merchant_id")
        if not merchant_id:
            return APIResponse.error(
                message="merchant_id is required.", status_code=400
            )

        serializer = MerchantReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        report = AnalyticsService.get_merchant_report(
            merchant_id=merchant_id,
            report_type=vd.get("report_type", "revenue"),
            date_from=vd.get("date_from"),
            date_to=vd.get("date_to"),
            status_filter=vd.get("status"),
            currency=vd.get("currency"),
            payment_method=vd.get("payment_method"),
            gateway=vd.get("gateway"),
        )

        export_fmt = vd.get("export_format", "json")
        if export_fmt == "csv":
            return ExportService.export_csv(
                report.get("rows", []),
                filename=f"{vd.get('report_type', 'report')}_report.csv",
            )

        return APIResponse.success(
            data=report, message="Report generated successfully."
        )


# ──────────────────────────────────────────────────────────
# RECONCILIATION
# ──────────────────────────────────────────────────────────
class ReconciliationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Financial Reconciliation",
        description="Compare orders, payments, and refunds to detect financial inconsistencies.",
        parameters=[
            OpenApiParameter(name="merchant_id", required=True, type=str),
        ],
    )
    def get(self, request):
        merchant_id = request.query_params.get("merchant_id")
        if not merchant_id:
            return APIResponse.error(
                message="merchant_id is required.", status_code=400
            )

        data = AnalyticsService.get_reconciliation(merchant_id)
        return APIResponse.success(
            data=data, message="Reconciliation report generated."
        )


# ──────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ──────────────────────────────────────────────────────────
class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Admin System-wide Dashboard",
        description="Returns system-wide KPIs for total merchants, customers, payments, refunds, webhooks.",
    )
    def get(self, request):
        data = AnalyticsService.get_admin_dashboard()
        return APIResponse.success(
            data=data, message="Admin dashboard metrics retrieved."
        )


# ──────────────────────────────────────────────────────────
# COUPON CRUD & VALIDATION
# ──────────────────────────────────────────────────────────
class CouponListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List Coupons",
        parameters=[
            OpenApiParameter(name="merchant_id", required=False, type=str),
        ],
        responses={200: CouponSerializer(many=True)},
    )
    def get(self, request):
        from orders.models import Coupon

        merchant_id = request.query_params.get("merchant_id")
        qs = Coupon.objects.all()
        if merchant_id:
            qs = qs.filter(merchant_id=merchant_id)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = CouponSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create Coupon",
        request=CouponCreateSerializer,
        responses={201: CouponSerializer},
    )
    def post(self, request):
        serializer = CouponCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        merchant_id = request.data.get("merchant_id")
        if not merchant_id:
            return APIResponse.error(
                message="merchant_id is required.", status_code=400
            )

        coupon = CouponService.create_coupon(merchant_id, serializer.validated_data)
        return APIResponse.success(
            data=CouponSerializer(coupon).data,
            message="Coupon created successfully.",
            status_code=201,
        )


class CouponDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update Coupon",
        request=CouponCreateSerializer,
        responses={200: CouponSerializer},
    )
    def patch(self, request, coupon_id):
        coupon = CouponService.update_coupon(coupon_id, request.data)
        return APIResponse.success(
            data=CouponSerializer(coupon).data, message="Coupon updated."
        )

    @extend_schema(summary="Delete (Disable) Coupon")
    def delete(self, request, coupon_id):
        CouponService.delete_coupon(coupon_id)
        return APIResponse.success(message="Coupon disabled.")


class CouponValidateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Validate Coupon", request=CouponValidateSerializer)
    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        result = CouponService.validate_coupon(
            code=vd["code"],
            order_amount=vd["order_amount"],
            merchant_id=request.data.get("merchant_id"),
        )
        return APIResponse.success(data=result, message="Coupon is valid.")


class CouponApplyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Apply Coupon", request=CouponValidateSerializer)
    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        result = CouponService.apply_coupon(
            code=vd["code"],
            order_amount=vd["order_amount"],
            merchant_id=request.data.get("merchant_id"),
        )
        return APIResponse.success(data=result, message="Coupon applied successfully.")


# ──────────────────────────────────────────────────────────
# INVOICE APIS
# ──────────────────────────────────────────────────────────
class InvoiceListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List Invoices",
        parameters=[OpenApiParameter(name="merchant_id", required=False, type=str)],
        responses={200: InvoiceSerializer(many=True)},
    )
    def get(self, request):
        merchant_id = request.query_params.get("merchant_id")
        qs = InvoiceService.list_invoices(merchant_id)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = InvoiceSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class InvoiceGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Generate Invoice for an Order")
    def post(self, request):
        from orders.models import Order

        order_number = request.data.get("order_number")
        if not order_number:
            return APIResponse.error(
                message="order_number is required.", status_code=400
            )

        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            raise ResourceNotFoundError(detail="Order not found.")

        invoice = InvoiceService.create_invoice(order)
        return APIResponse.success(
            data=InvoiceSerializer(invoice).data,
            message="Invoice generated successfully.",
            status_code=201,
        )


class InvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Invoice Details", responses={200: InvoiceSerializer})
    def get(self, request, invoice_number):
        invoice = InvoiceService.get_invoice_by_id(invoice_number)
        if not invoice:
            raise ResourceNotFoundError(detail="Invoice not found.")
        return APIResponse.success(data=InvoiceSerializer(invoice).data)


class InvoiceDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Download Invoice PDF")
    def get(self, request, invoice_number):
        invoice = InvoiceService.get_invoice_by_id(invoice_number)
        if not invoice:
            raise ResourceNotFoundError(detail="Invoice not found.")

        pdf_bytes = InvoiceService.generate_pdf(invoice)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{invoice_number}.pdf"'
        return response


class InvoiceRegenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Regenerate Invoice PDF")
    def post(self, request, invoice_number):
        invoice = InvoiceService.get_invoice_by_id(invoice_number)
        if not invoice:
            raise ResourceNotFoundError(detail="Invoice not found.")

        pdf_bytes = InvoiceService.generate_pdf(invoice)
        return APIResponse.success(
            data={"invoice_number": invoice_number, "pdf_size_bytes": len(pdf_bytes)},
            message="Invoice PDF regenerated.",
        )
