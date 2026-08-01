from analytics.views import (
    AdminDashboardView,
    ChartDataView,
    CouponApplyView,
    CouponDetailView,
    CouponListCreateView,
    CouponValidateView,
    InvoiceDetailView,
    InvoiceDownloadView,
    InvoiceGenerateView,
    InvoiceListView,
    InvoiceRegenerateView,
    MerchantDashboardView,
    MerchantReportView,
    ReconciliationView,
    SettlementReportView,
)
from django.urls import path

app_name = "analytics"

urlpatterns = [
    # ── Dashboard & Charts ──────────────────────────
    path("dashboard/", MerchantDashboardView.as_view(), name="merchant_dashboard"),
    path("charts/", ChartDataView.as_view(), name="chart_data"),
    path("settlements/", SettlementReportView.as_view(), name="settlement_report"),
    path("reports/", MerchantReportView.as_view(), name="merchant_report"),
    path("reconciliation/", ReconciliationView.as_view(), name="reconciliation"),
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin_dashboard"),
    # ── Coupons ─────────────────────────────────────
    path("coupons/", CouponListCreateView.as_view(), name="coupon_list_create"),
    path("coupons/validate/", CouponValidateView.as_view(), name="coupon_validate"),
    path("coupons/apply/", CouponApplyView.as_view(), name="coupon_apply"),
    path("coupons/<str:coupon_id>/", CouponDetailView.as_view(), name="coupon_detail"),
    # ── Invoices ────────────────────────────────────
    path("invoices/", InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/generate/", InvoiceGenerateView.as_view(), name="invoice_generate"),
    path(
        "invoices/<str:invoice_number>/",
        InvoiceDetailView.as_view(),
        name="invoice_detail",
    ),
    path(
        "invoices/<str:invoice_number>/download/",
        InvoiceDownloadView.as_view(),
        name="invoice_download",
    ),
    path(
        "invoices/<str:invoice_number>/regenerate/",
        InvoiceRegenerateView.as_view(),
        name="invoice_regenerate",
    ),
]
