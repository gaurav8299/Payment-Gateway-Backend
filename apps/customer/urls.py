from customer.views import (
    CustomerDetailView,
    CustomerListCreateView,
    CustomerPaymentMethodListCreateView,
)
from django.urls import path

app_name = "customer"

urlpatterns = [
    path("", CustomerListCreateView.as_view(), name="customer_list_create"),
    path("<uuid:customer_id>/", CustomerDetailView.as_view(), name="customer_detail"),
    path(
        "<uuid:customer_id>/payment-methods/",
        CustomerPaymentMethodListCreateView.as_view(),
        name="customer_payment_methods",
    ),
]
