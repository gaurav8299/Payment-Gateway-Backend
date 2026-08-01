from django.urls import path
from refunds.views import (
    RefundDetailView,
    RefundLedgerView,
    RefundListCreateView,
    RefundMetricsView,
)

app_name = "refunds"

urlpatterns = [
    path("", RefundListCreateView.as_view(), name="refund_list_create"),
    path("metrics/", RefundMetricsView.as_view(), name="refund_metrics"),
    path("<str:refund_id>/", RefundDetailView.as_view(), name="refund_detail"),
    path("<str:refund_id>/ledger/", RefundLedgerView.as_view(), name="refund_ledger"),
]
