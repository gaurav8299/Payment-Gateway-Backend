from django.urls import path
from payments.views import (
    PaymentCaptureView,
    PaymentDetailView,
    PaymentLedgerView,
    PaymentListCreateView,
    PaymentVoidView,
)

app_name = "payments"

urlpatterns = [
    path("", PaymentListCreateView.as_view(), name="payment_list_create"),
    path("<str:payment_id>/", PaymentDetailView.as_view(), name="payment_detail"),
    path(
        "<str:payment_id>/capture/",
        PaymentCaptureView.as_view(),
        name="payment_capture",
    ),
    path("<str:payment_id>/void/", PaymentVoidView.as_view(), name="payment_void"),
    path(
        "<str:payment_id>/ledger/", PaymentLedgerView.as_view(), name="payment_ledger"
    ),
]
