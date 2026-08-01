from django.urls import path
from orders.views import (
    OrderCancelView,
    OrderDetailView,
    OrderExpireView,
    OrderListCreateView,
)

app_name = "orders"

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="order_list_create"),
    path("<str:order_identifier>/", OrderDetailView.as_view(), name="order_detail"),
    path(
        "<str:order_identifier>/cancel/", OrderCancelView.as_view(), name="order_cancel"
    ),
    path(
        "<str:order_identifier>/expire/", OrderExpireView.as_view(), name="order_expire"
    ),
]
