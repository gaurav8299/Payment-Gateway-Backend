from django.urls import path
from wallet.views import (
    WalletCreditView,
    WalletDebitView,
    WalletDetailView,
    WalletFreezeView,
    WalletGetOrCreateView,
    WalletTransactionHistoryView,
    WalletUnfreezeView,
)

app_name = "wallet"

urlpatterns = [
    path(
        "customer/<uuid:customer_id>/",
        WalletGetOrCreateView.as_view(),
        name="wallet_customer",
    ),
    path("<uuid:wallet_id>/", WalletDetailView.as_view(), name="wallet_detail"),
    path("<uuid:wallet_id>/credit/", WalletCreditView.as_view(), name="wallet_credit"),
    path("<uuid:wallet_id>/debit/", WalletDebitView.as_view(), name="wallet_debit"),
    path("<uuid:wallet_id>/freeze/", WalletFreezeView.as_view(), name="wallet_freeze"),
    path(
        "<uuid:wallet_id>/unfreeze/",
        WalletUnfreezeView.as_view(),
        name="wallet_unfreeze",
    ),
    path(
        "<uuid:wallet_id>/transactions/",
        WalletTransactionHistoryView.as_view(),
        name="wallet_transactions",
    ),
]
