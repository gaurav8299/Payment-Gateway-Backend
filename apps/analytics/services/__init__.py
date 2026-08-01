import logging
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate, TruncHour, TruncMonth, TruncWeek
from django.utils import timezone
from orders.models import Order, OrderStatus
from payments.models import Payment, PaymentStatus
from refunds.models import Refund, RefundStatus
from wallet.models import WalletTransaction

logger = logging.getLogger("payment_gateway")

# ── Cache TTLs ──────────────────────────────────────────
DASHBOARD_CACHE_TTL = 300  # 5 minutes
CHART_CACHE_TTL = 600  # 10 minutes
REPORT_CACHE_TTL = 900  # 15 minutes


class AnalyticsService:
    """
    Analytics Service providing merchant and admin dashboard metrics,
    chart data, and settlement summaries.  All heavy aggregations are
    cached in Redis and invalidated on new payment/refund events.
    """

    # ── Merchant Dashboard Metrics ──────────────────────
    @staticmethod
    def get_merchant_dashboard(merchant_id: str) -> dict:
        cache_key = f"analytics:merchant:{merchant_id}:dashboard"
        cached = cache.get(cache_key)
        if cached:
            return cached

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        year_start = today_start.replace(month=1, day=1)

        base_qs = Payment.objects.filter(merchant_id=merchant_id)
        captured_qs = base_qs.filter(status=PaymentStatus.CAPTURED)
        failed_qs = base_qs.filter(status=PaymentStatus.FAILED)
        refund_qs = Refund.objects.filter(
            merchant_id=merchant_id, status=RefundStatus.SUCCESS
        )

        total_revenue = captured_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        today_revenue = captured_qs.filter(created_at__gte=today_start).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        weekly_revenue = captured_qs.filter(created_at__gte=week_start).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        monthly_revenue = captured_qs.filter(created_at__gte=month_start).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        yearly_revenue = captured_qs.filter(created_at__gte=year_start).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        successful_count = captured_qs.count()
        failed_count = failed_qs.count()
        total_payments = base_qs.count()

        refund_count = refund_qs.count()
        refund_amount = refund_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )

        avg_txn = captured_qs.aggregate(avg=Avg("amount"))["avg"] or Decimal("0.00")
        success_rate = (
            round((successful_count / total_payments * 100), 2)
            if total_payments
            else 0.0
        )
        refund_rate = (
            round((refund_count / successful_count * 100), 2)
            if successful_count
            else 0.0
        )

        # Top payment methods
        top_methods = list(
            captured_qs.values("payment_method")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")[:5]
        )

        # Gateway usage
        gateway_usage = list(
            captured_qs.values("gateway")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )

        # Currency breakdown
        currency_breakdown = list(
            captured_qs.values("currency")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )

        result = {
            "total_revenue": str(total_revenue),
            "today_revenue": str(today_revenue),
            "weekly_revenue": str(weekly_revenue),
            "monthly_revenue": str(monthly_revenue),
            "yearly_revenue": str(yearly_revenue),
            "successful_payments": successful_count,
            "failed_payments": failed_count,
            "refund_count": refund_count,
            "refund_amount": str(refund_amount),
            "average_transaction_value": str(round(avg_txn, 2)),
            "payment_success_rate": success_rate,
            "refund_rate": refund_rate,
            "top_payment_methods": top_methods,
            "gateway_usage": gateway_usage,
            "currency_breakdown": currency_breakdown,
        }
        cache.set(cache_key, result, DASHBOARD_CACHE_TTL)
        return result

    # ── Chart Data ──────────────────────────────────────
    @staticmethod
    def get_chart_data(
        merchant_id: str, granularity: str = "daily", days: int = 30
    ) -> dict:
        """
        Returns time-series chart data for revenue, payment counts,
        and refund timelines.
        Granularity: daily | weekly | monthly | hourly
        """
        cache_key = f"analytics:merchant:{merchant_id}:chart:{granularity}:{days}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        now = timezone.now()
        start_date = now - timedelta(days=days)

        trunc_map = {
            "hourly": TruncHour,
            "daily": TruncDate,
            "weekly": TruncWeek,
            "monthly": TruncMonth,
        }
        trunc_fn = trunc_map.get(granularity, TruncDate)

        captured_qs = Payment.objects.filter(
            merchant_id=merchant_id,
            status=PaymentStatus.CAPTURED,
            created_at__gte=start_date,
        )
        refund_qs = Refund.objects.filter(
            merchant_id=merchant_id,
            status=RefundStatus.SUCCESS,
            created_at__gte=start_date,
        )

        revenue_timeline = list(
            captured_qs.annotate(period=trunc_fn("created_at"))
            .values("period")
            .annotate(revenue=Sum("amount"), count=Count("id"))
            .order_by("period")
        )

        refund_timeline = list(
            refund_qs.annotate(period=trunc_fn("created_at"))
            .values("period")
            .annotate(refunded=Sum("amount"), count=Count("id"))
            .order_by("period")
        )

        method_distribution = list(
            captured_qs.values("payment_method")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )

        status_distribution = list(
            Payment.objects.filter(merchant_id=merchant_id, created_at__gte=start_date)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Serialize datetime objects
        for item in revenue_timeline:
            item["period"] = str(item["period"])
            item["revenue"] = str(item["revenue"])
        for item in refund_timeline:
            item["period"] = str(item["period"])
            item["refunded"] = str(item["refunded"])
        for item in method_distribution:
            item["total"] = str(item["total"])

        result = {
            "granularity": granularity,
            "days": days,
            "revenue_timeline": revenue_timeline,
            "refund_timeline": refund_timeline,
            "payment_method_distribution": method_distribution,
            "status_distribution": status_distribution,
        }
        cache.set(cache_key, result, CHART_CACHE_TTL)
        return result

    # ── Settlement Reports ──────────────────────────────
    @staticmethod
    def get_settlement_report(merchant_id: str) -> dict:
        cache_key = f"analytics:merchant:{merchant_id}:settlement"
        cached = cache.get(cache_key)
        if cached:
            return cached

        captured_qs = Payment.objects.filter(
            merchant_id=merchant_id, status=PaymentStatus.CAPTURED
        )
        settled_qs = Payment.objects.filter(
            merchant_id=merchant_id, status=PaymentStatus.SETTLED
        )
        refund_qs = Refund.objects.filter(
            merchant_id=merchant_id, status=RefundStatus.SUCCESS
        )

        total_captured = captured_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        total_settled = settled_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        total_refunded = refund_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        pending_settlement = total_captured - total_settled

        result = {
            "total_captured": str(total_captured),
            "total_settled": str(total_settled),
            "total_refunded": str(total_refunded),
            "pending_settlement": str(pending_settlement),
            "settled_payments_count": settled_qs.count(),
            "pending_payments_count": captured_qs.count(),
        }
        cache.set(cache_key, result, REPORT_CACHE_TTL)
        return result

    # ── Merchant Reports (filterable) ───────────────────
    @staticmethod
    def get_merchant_report(
        merchant_id: str,
        report_type: str = "revenue",
        date_from=None,
        date_to=None,
        status_filter=None,
        currency=None,
        payment_method=None,
        gateway=None,
    ) -> dict:
        """
        Generate filterable merchant report.
        report_type: revenue | refund | order | customer | wallet | transaction
        """
        now = timezone.now()
        if not date_from:
            date_from = now - timedelta(days=30)
        if not date_to:
            date_to = now

        if report_type == "revenue":
            qs = Payment.objects.filter(
                merchant_id=merchant_id,
                status=PaymentStatus.CAPTURED,
                created_at__range=(date_from, date_to),
            )
            if currency:
                qs = qs.filter(currency=currency)
            if payment_method:
                qs = qs.filter(payment_method=payment_method)
            if gateway:
                qs = qs.filter(gateway=gateway)

            agg = qs.aggregate(
                total=Sum("amount"), count=Count("id"), avg=Avg("amount")
            )
            rows = list(
                qs.values(
                    "payment_id",
                    "amount",
                    "currency",
                    "payment_method",
                    "gateway",
                    "status",
                    "created_at",
                ).order_by("-created_at")
            )
            return {
                "summary": {k: str(v) if v else "0" for k, v in agg.items()},
                "rows": rows,
            }

        elif report_type == "refund":
            qs = Refund.objects.filter(
                merchant_id=merchant_id,
                created_at__range=(date_from, date_to),
            )
            if status_filter:
                qs = qs.filter(status=status_filter)
            if currency:
                qs = qs.filter(currency=currency)

            agg = qs.aggregate(total=Sum("amount"), count=Count("id"))
            rows = list(
                qs.values(
                    "refund_id", "amount", "currency", "status", "reason", "created_at"
                ).order_by("-created_at")
            )
            return {
                "summary": {k: str(v) if v else "0" for k, v in agg.items()},
                "rows": rows,
            }

        elif report_type == "order":
            qs = Order.objects.filter(
                merchant_id=merchant_id,
                created_at__range=(date_from, date_to),
            )
            if status_filter:
                qs = qs.filter(status=status_filter)
            if currency:
                qs = qs.filter(currency=currency)

            agg = qs.aggregate(total=Sum("amount"), count=Count("id"))
            rows = list(
                qs.values(
                    "order_number", "amount", "currency", "status", "created_at"
                ).order_by("-created_at")
            )
            return {
                "summary": {k: str(v) if v else "0" for k, v in agg.items()},
                "rows": rows,
            }

        elif report_type == "wallet":
            qs = WalletTransaction.objects.filter(
                wallet__merchant_id=merchant_id,
                created_at__range=(date_from, date_to),
            )
            agg = qs.aggregate(
                total_credits=Sum("amount", filter=Q(type="CREDIT")),
                total_debits=Sum("amount", filter=Q(type="DEBIT")),
                count=Count("id"),
            )
            rows = list(
                qs.values(
                    "transaction_number", "amount", "type", "status", "created_at"
                ).order_by("-created_at")
            )
            return {
                "summary": {k: str(v) if v else "0" for k, v in agg.items()},
                "rows": rows,
            }

        else:
            # transaction report – all payments
            qs = Payment.objects.filter(
                merchant_id=merchant_id,
                created_at__range=(date_from, date_to),
            )
            if status_filter:
                qs = qs.filter(status=status_filter)
            if currency:
                qs = qs.filter(currency=currency)
            if payment_method:
                qs = qs.filter(payment_method=payment_method)
            if gateway:
                qs = qs.filter(gateway=gateway)

            agg = qs.aggregate(total=Sum("amount"), count=Count("id"))
            rows = list(
                qs.values(
                    "payment_id",
                    "amount",
                    "currency",
                    "payment_method",
                    "gateway",
                    "status",
                    "created_at",
                ).order_by("-created_at")
            )
            return {
                "summary": {k: str(v) if v else "0" for k, v in agg.items()},
                "rows": rows,
            }

    # ── Admin System-wide Dashboard ─────────────────────
    @staticmethod
    def get_admin_dashboard() -> dict:
        cache_key = "analytics:admin:dashboard"
        cached = cache.get(cache_key)
        if cached:
            return cached

        from customer.models import CustomerProfile
        from merchant.models import MerchantProfile
        from webhooks.models import WebhookDelivery

        total_merchants = MerchantProfile.objects.count()
        total_customers = CustomerProfile.objects.count()
        total_orders = Order.objects.count()
        total_payments = Payment.objects.count()
        total_refunds = Refund.objects.count()

        revenue = Payment.objects.filter(status=PaymentStatus.CAPTURED).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        failed_payments = Payment.objects.filter(status=PaymentStatus.FAILED).count()
        pending_refunds = Refund.objects.filter(status=RefundStatus.CREATED).count()

        webhook_stats = {
            "total_deliveries": WebhookDelivery.objects.count(),
            "successful": WebhookDelivery.objects.filter(status="SUCCESS").count(),
            "failed": WebhookDelivery.objects.filter(status="FAILED").count(),
        }

        result = {
            "total_merchants": total_merchants,
            "total_customers": total_customers,
            "total_orders": total_orders,
            "total_payments": total_payments,
            "total_refunds": total_refunds,
            "total_revenue": str(revenue),
            "failed_payments": failed_payments,
            "pending_refunds": pending_refunds,
            "webhook_statistics": webhook_stats,
        }
        cache.set(cache_key, result, DASHBOARD_CACHE_TTL)
        return result

    # ── Financial Reconciliation ────────────────────────
    @staticmethod
    def get_reconciliation(merchant_id: str) -> dict:
        """
        Compare orders, payments, refunds, and wallet transactions
        to detect inconsistencies.
        """
        orders_total = Order.objects.filter(
            merchant_id=merchant_id, status=OrderStatus.PAID
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        payments_total = Payment.objects.filter(
            merchant_id=merchant_id, status=PaymentStatus.CAPTURED
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        refunds_total = Refund.objects.filter(
            merchant_id=merchant_id, status=RefundStatus.SUCCESS
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        net_revenue = payments_total - refunds_total
        discrepancy = orders_total - payments_total

        return {
            "orders_total": str(orders_total),
            "payments_total": str(payments_total),
            "refunds_total": str(refunds_total),
            "net_revenue": str(net_revenue),
            "discrepancy": str(discrepancy),
            "is_reconciled": discrepancy == Decimal("0.00"),
        }

    # ── Cache Invalidation ──────────────────────────────
    @staticmethod
    def invalidate_merchant_cache(merchant_id: str):
        """Called when a new payment/refund modifies merchant financial data."""
        patterns = [
            f"analytics:merchant:{merchant_id}:dashboard",
            f"analytics:merchant:{merchant_id}:settlement",
        ]
        for key in patterns:
            cache.delete(key)
        # Also blow chart caches for all granularities
        for g in ("hourly", "daily", "weekly", "monthly"):
            for d in (7, 30, 90, 365):
                cache.delete(f"analytics:merchant:{merchant_id}:chart:{g}:{d}")
        cache.delete("analytics:admin:dashboard")
        logger.info(f"Invalidated analytics cache for merchant {merchant_id}")
