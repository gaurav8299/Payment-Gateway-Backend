import logging

from analytics.services import AnalyticsService
from analytics.services.invoice_service import InvoiceService
from celery import shared_task

logger = logging.getLogger("payment_gateway")


@shared_task(
    name="analytics.tasks.generate_invoice_pdf",
    queue="analytics_queue",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def generate_invoice_pdf_task(self, invoice_number: str):
    """
    Async Celery task to generate PDF for an invoice.
    """
    try:
        invoice = InvoiceService.get_invoice_by_id(invoice_number)
        if not invoice:
            logger.error(f"Invoice {invoice_number} not found for PDF generation")
            return

        pdf_bytes = InvoiceService.generate_pdf(invoice)
        logger.info(
            f"PDF generated for invoice {invoice_number}: {len(pdf_bytes)} bytes"
        )
        return {"invoice_number": invoice_number, "pdf_size_bytes": len(pdf_bytes)}
    except Exception as exc:
        logger.exception(f"Invoice PDF generation failed for {invoice_number}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="analytics.tasks.generate_daily_summary",
    queue="analytics_queue",
)
def generate_daily_summary_task():
    """
    Scheduled Celery task to pre-compute daily analytics summaries.
    """
    from merchant.models import MerchantProfile

    merchants = MerchantProfile.objects.filter(status="ACTIVE").values_list(
        "id", flat=True
    )
    for merchant_id in merchants:
        try:
            AnalyticsService.invalidate_merchant_cache(str(merchant_id))
            AnalyticsService.get_merchant_dashboard(str(merchant_id))
            AnalyticsService.get_settlement_report(str(merchant_id))
            logger.info(f"Daily summary pre-computed for merchant {merchant_id}")
        except Exception as exc:
            logger.exception(f"Daily summary failed for merchant {merchant_id}: {exc}")

    AnalyticsService.get_admin_dashboard()
    logger.info("Daily summary completed for admin dashboard")


@shared_task(
    name="analytics.tasks.generate_weekly_summary",
    queue="analytics_queue",
)
def generate_weekly_summary_task():
    """
    Scheduled Celery task to pre-compute weekly chart data.
    """
    from merchant.models import MerchantProfile

    merchants = MerchantProfile.objects.filter(status="ACTIVE").values_list(
        "id", flat=True
    )
    for merchant_id in merchants:
        try:
            AnalyticsService.get_chart_data(str(merchant_id), "weekly", 30)
            logger.info(f"Weekly chart data pre-computed for merchant {merchant_id}")
        except Exception as exc:
            logger.exception(f"Weekly summary failed for merchant {merchant_id}: {exc}")


@shared_task(
    name="analytics.tasks.generate_monthly_summary",
    queue="analytics_queue",
)
def generate_monthly_summary_task():
    """
    Scheduled Celery task to pre-compute monthly analytics data.
    """
    from merchant.models import MerchantProfile

    merchants = MerchantProfile.objects.filter(status="ACTIVE").values_list(
        "id", flat=True
    )
    for merchant_id in merchants:
        try:
            AnalyticsService.get_chart_data(str(merchant_id), "monthly", 365)
            logger.info(f"Monthly chart data pre-computed for merchant {merchant_id}")
        except Exception as exc:
            logger.exception(
                f"Monthly summary failed for merchant {merchant_id}: {exc}"
            )
