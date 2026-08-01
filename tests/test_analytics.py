from decimal import Decimal

import pytest
from accounts.models import UserRole
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from analytics.services import AnalyticsService
from analytics.services.coupon_service import CouponService
from analytics.services.export_service import ExportService
from analytics.services.invoice_service import InvoiceService
from customer.models import CustomerProfile
from django.urls import reverse
from merchant.models import MerchantProfile
from orders.models import Coupon, CouponStatus, Order, OrderStatus
from payments.models import Payment, PaymentGateway, PaymentMethod, PaymentStatus
from refunds.models import Refund, RefundStatus
from rest_framework import status as http_status


def _setup_merchant_and_auth(api_client):
    """Helper to create a merchant user with profile and auth tokens."""
    user = UserRepository.create_user(
        email="analytics_merchant@test.com",
        password="Password123!",
        role=UserRole.MERCHANT,
    )
    merchant = MerchantProfile.objects.create(
        user=user,
        business_name="Analytics Test Corp",
        legal_business_name="Analytics Test Corp Pvt Ltd",
        support_email="support@analyticstest.com",
        support_phone="+911234567890",
        address="Analytics HQ, Mumbai",
        status="ACTIVE",
    )
    customer = CustomerProfile.objects.create(
        name="Test Analytics Customer",
        email="analytics_customer@test.com",
        phone="+919876543210",
        merchant=merchant,
    )
    _, tokens = AuthService.login_user("analytics_merchant@test.com", "Password123!")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return user, merchant, customer


def _create_order(merchant, customer, amount="5000.00", status=OrderStatus.PAID):
    import uuid

    return Order.objects.create(
        order_number=f"ord_{uuid.uuid4().hex[:24]}",
        merchant=merchant,
        customer=customer,
        amount=Decimal(amount),
        currency="INR",
        status=status,
    )


def _create_payment(
    order, merchant, customer, amount="5000.00", status=PaymentStatus.CAPTURED
):
    import uuid

    return Payment.objects.create(
        payment_id=f"pay_{uuid.uuid4().hex[:24]}",
        order=order,
        merchant=merchant,
        customer=customer,
        amount=Decimal(amount),
        currency="INR",
        payment_method=PaymentMethod.CARD,
        gateway=PaymentGateway.DUMMY,
        status=status,
    )


def _create_refund(
    payment, order, merchant, customer, amount="1000.00", status=RefundStatus.SUCCESS
):
    import uuid

    return Refund.objects.create(
        refund_id=f"rfnd_{uuid.uuid4().hex[:24]}",
        payment=payment,
        order=order,
        merchant=merchant,
        customer=customer,
        amount=Decimal(amount),
        currency="INR",
        status=status,
    )


# ══════════════════════════════════════════════════════════
# ANALYTICS SERVICE TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestAnalyticsService:
    def test_merchant_dashboard_metrics(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer, "5000.00", PaymentStatus.CAPTURED)
        _create_payment(order, merchant, customer, "3000.00", PaymentStatus.FAILED)
        _create_refund(
            Payment.objects.filter(
                merchant=merchant, status=PaymentStatus.CAPTURED
            ).first(),
            order,
            merchant,
            customer,
            "1000.00",
        )

        dashboard = AnalyticsService.get_merchant_dashboard(str(merchant.id))
        assert Decimal(dashboard["total_revenue"]) == Decimal("5000.00")
        assert dashboard["successful_payments"] == 1
        assert dashboard["failed_payments"] == 1
        assert dashboard["refund_count"] == 1
        assert Decimal(dashboard["refund_amount"]) == Decimal("1000.00")
        assert dashboard["payment_success_rate"] > 0

    def test_chart_data(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer, "2500.00")

        chart = AnalyticsService.get_chart_data(str(merchant.id), "daily", 30)
        assert "revenue_timeline" in chart
        assert "payment_method_distribution" in chart
        assert chart["granularity"] == "daily"

    def test_settlement_report(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer, "5000.00", PaymentStatus.CAPTURED)

        settlement = AnalyticsService.get_settlement_report(str(merchant.id))
        assert Decimal(settlement["total_captured"]) == Decimal("5000.00")
        assert "pending_settlement" in settlement

    def test_reconciliation(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer, "5000.00", OrderStatus.PAID)
        _create_payment(order, merchant, customer, "5000.00", PaymentStatus.CAPTURED)

        recon = AnalyticsService.get_reconciliation(str(merchant.id))
        assert "orders_total" in recon
        assert "payments_total" in recon
        assert "is_reconciled" in recon

    def test_admin_dashboard(self, api_client):
        _setup_merchant_and_auth(api_client)
        dashboard = AnalyticsService.get_admin_dashboard()
        assert "total_merchants" in dashboard
        assert "total_customers" in dashboard
        assert "webhook_statistics" in dashboard

    def test_merchant_report_revenue(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer, "7000.00")

        report = AnalyticsService.get_merchant_report(str(merchant.id), "revenue")
        assert "summary" in report
        assert "rows" in report

    def test_cache_invalidation(self, api_client):
        _, merchant, _ = _setup_merchant_and_auth(api_client)
        # Should not raise
        AnalyticsService.invalidate_merchant_cache(str(merchant.id))


# ══════════════════════════════════════════════════════════
# COUPON SERVICE TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestCouponService:
    def test_create_and_validate_coupon(self, api_client):
        _, merchant, _ = _setup_merchant_and_auth(api_client)

        coupon = CouponService.create_coupon(
            str(merchant.id),
            {
                "code": "SAVE20",
                "discount_type": "PERCENTAGE",
                "discount_value": "20",
                "max_discount_amount": "500",
                "min_order_amount": "100",
                "usage_limit": 50,
            },
        )
        assert coupon.code == "SAVE20"
        assert coupon.discount_value == Decimal("20")

        result = CouponService.validate_coupon(
            "SAVE20", Decimal("1000.00"), str(merchant.id)
        )
        assert result["valid"] is True
        assert Decimal(result["calculated_discount"]) == Decimal("200.00")
        assert Decimal(result["final_amount"]) == Decimal("800.00")

    def test_percentage_coupon_max_cap(self, api_client):
        _, merchant, _ = _setup_merchant_and_auth(api_client)

        CouponService.create_coupon(
            str(merchant.id),
            {
                "code": "BIG50",
                "discount_type": "PERCENTAGE",
                "discount_value": "50",
                "max_discount_amount": "300",
                "min_order_amount": "0",
            },
        )

        result = CouponService.validate_coupon("BIG50", Decimal("5000.00"))
        # 50% of 5000 = 2500, but max is 300
        assert Decimal(result["calculated_discount"]) == Decimal("300.00")

    def test_fixed_coupon(self, api_client):
        _, merchant, _ = _setup_merchant_and_auth(api_client)

        CouponService.create_coupon(
            str(merchant.id),
            {
                "code": "FLAT100",
                "discount_type": "FIXED",
                "discount_value": "100",
            },
        )

        result = CouponService.validate_coupon("FLAT100", Decimal("500.00"))
        assert Decimal(result["calculated_discount"]) == Decimal("100.00")

    def test_apply_coupon_increments_usage(self, api_client):
        _, merchant, _ = _setup_merchant_and_auth(api_client)

        CouponService.create_coupon(
            str(merchant.id),
            {
                "code": "USEONCE",
                "discount_type": "PERCENTAGE",
                "discount_value": "10",
                "usage_limit": 5,
            },
        )

        CouponService.apply_coupon("USEONCE", Decimal("1000.00"))
        coupon = Coupon.objects.get(code="USEONCE")
        assert coupon.used_count == 1

    def test_coupon_min_order_validation(self, api_client):
        from common.exceptions import BusinessLogicError

        _, merchant, _ = _setup_merchant_and_auth(api_client)

        CouponService.create_coupon(
            str(merchant.id),
            {
                "code": "MINTEST",
                "discount_type": "PERCENTAGE",
                "discount_value": "10",
                "min_order_amount": "500",
            },
        )

        with pytest.raises(BusinessLogicError):
            CouponService.validate_coupon("MINTEST", Decimal("100.00"))

    def test_update_and_delete_coupon(self, api_client):
        _, merchant, _ = _setup_merchant_and_auth(api_client)

        coupon = CouponService.create_coupon(
            str(merchant.id),
            {
                "code": "UPDEL",
                "discount_type": "PERCENTAGE",
                "discount_value": "15",
            },
        )

        updated = CouponService.update_coupon(str(coupon.id), {"usage_limit": 200})
        assert updated.usage_limit == 200

        deleted = CouponService.delete_coupon(str(coupon.id))
        assert deleted.status == CouponStatus.DISABLED


# ══════════════════════════════════════════════════════════
# INVOICE SERVICE TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestInvoiceService:
    def test_create_invoice(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer, "10000.00")

        invoice = InvoiceService.create_invoice(order)
        assert invoice.invoice_number.startswith("inv_")
        assert invoice.subtotal == Decimal("10000.00")
        assert invoice.tax_amount == Decimal("1800.00")
        assert invoice.total_amount == Decimal("11800.00")

    def test_generate_pdf(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer, "5000.00")
        invoice = InvoiceService.create_invoice(order)

        pdf_bytes = InvoiceService.generate_pdf(invoice)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100
        # Verify it starts with PDF magic bytes
        assert pdf_bytes[:5] == b"%PDF-"

    def test_list_invoices(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer, "2000.00")
        InvoiceService.create_invoice(order)

        invoices = InvoiceService.list_invoices(str(merchant.id))
        assert invoices.count() >= 1


# ══════════════════════════════════════════════════════════
# EXPORT SERVICE TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestExportService:
    def test_export_csv(self):
        rows = [
            {"id": "1", "amount": "100.00", "status": "CAPTURED"},
            {"id": "2", "amount": "200.00", "status": "FAILED"},
        ]
        response = ExportService.export_csv(rows, filename="test_export.csv")
        assert response["Content-Type"] == "text/csv"
        assert "test_export.csv" in response["Content-Disposition"]
        content = response.content.decode("utf-8")
        assert "id,amount,status" in content
        assert "100.00" in content

    def test_export_json(self):
        data = {"summary": {"total": "300.00"}, "rows": []}
        response = ExportService.export_json(data, filename="test_export.json")
        assert response["Content-Type"] == "application/json"
        assert "test_export.json" in response["Content-Disposition"]

    def test_export_csv_empty(self):
        response = ExportService.export_csv([], filename="empty.csv")
        assert response["Content-Type"] == "text/csv"


# ══════════════════════════════════════════════════════════
# ANALYTICS API ENDPOINT TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestAnalyticsAPIEndpoints:
    def test_merchant_dashboard_api(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer)

        url = reverse("analytics:merchant_dashboard")
        res = api_client.get(url, {"merchant_id": str(merchant.id)})
        assert res.status_code == http_status.HTTP_200_OK
        assert res.data["success"] is True
        assert "total_revenue" in res.data["data"]

    def test_chart_data_api(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer)

        url = reverse("analytics:chart_data")
        res = api_client.get(
            url, {"merchant_id": str(merchant.id), "granularity": "daily", "days": 30}
        )
        assert res.status_code == http_status.HTTP_200_OK
        assert "revenue_timeline" in res.data["data"]

    def test_settlement_report_api(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer)

        url = reverse("analytics:settlement_report")
        res = api_client.get(url, {"merchant_id": str(merchant.id)})
        assert res.status_code == http_status.HTTP_200_OK

    def test_merchant_report_api(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer)

        url = reverse("analytics:merchant_report")
        res = api_client.get(
            url, {"merchant_id": str(merchant.id), "report_type": "revenue"}
        )
        assert res.status_code == http_status.HTTP_200_OK
        assert "summary" in res.data["data"]

    def test_merchant_report_csv_export(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer)

        url = reverse("analytics:merchant_report")
        res = api_client.get(
            url,
            {
                "merchant_id": str(merchant.id),
                "report_type": "revenue",
                "export_format": "csv",
            },
        )
        assert res["Content-Type"] == "text/csv"

    def test_reconciliation_api(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer)
        _create_payment(order, merchant, customer)

        url = reverse("analytics:reconciliation")
        res = api_client.get(url, {"merchant_id": str(merchant.id)})
        assert res.status_code == http_status.HTTP_200_OK
        assert "is_reconciled" in res.data["data"]

    def test_admin_dashboard_api(self, api_client):
        _setup_merchant_and_auth(api_client)

        url = reverse("analytics:admin_dashboard")
        res = api_client.get(url)
        assert res.status_code == http_status.HTTP_200_OK
        assert "total_merchants" in res.data["data"]


# ══════════════════════════════════════════════════════════
# COUPON API ENDPOINT TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestCouponAPIEndpoints:
    def test_coupon_crud_api(self, api_client):
        _, merchant, _ = _setup_merchant_and_auth(api_client)

        # Create
        url = reverse("analytics:coupon_list_create")
        res = api_client.post(
            url,
            {
                "merchant_id": str(merchant.id),
                "code": "API20",
                "discount_type": "PERCENTAGE",
                "discount_value": "20",
                "max_discount_amount": "500",
                "min_order_amount": "100",
            },
            format="json",
        )
        assert res.status_code == http_status.HTTP_201_CREATED

        coupon_id = res.data["data"]["id"]

        # List
        res = api_client.get(url, {"merchant_id": str(merchant.id)})
        assert res.status_code == http_status.HTTP_200_OK

        # Validate
        validate_url = reverse("analytics:coupon_validate")
        res = api_client.post(
            validate_url,
            {
                "code": "API20",
                "order_amount": "1000.00",
                "merchant_id": str(merchant.id),
            },
            format="json",
        )
        assert res.status_code == http_status.HTTP_200_OK
        assert res.data["data"]["valid"] is True

        # Apply
        apply_url = reverse("analytics:coupon_apply")
        res = api_client.post(
            apply_url,
            {
                "code": "API20",
                "order_amount": "1000.00",
                "merchant_id": str(merchant.id),
            },
            format="json",
        )
        assert res.status_code == http_status.HTTP_200_OK

        # Update
        detail_url = reverse("analytics:coupon_detail", args=[coupon_id])
        res = api_client.patch(detail_url, {"usage_limit": 200}, format="json")
        assert res.status_code == http_status.HTTP_200_OK

        # Delete (Disable)
        res = api_client.delete(detail_url)
        assert res.status_code == http_status.HTTP_200_OK


# ══════════════════════════════════════════════════════════
# INVOICE API ENDPOINT TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestInvoiceAPIEndpoints:
    def test_invoice_generate_and_download(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer, "8000.00")

        # Generate
        gen_url = reverse("analytics:invoice_generate")
        res = api_client.post(
            gen_url, {"order_number": order.order_number}, format="json"
        )
        assert res.status_code == http_status.HTTP_201_CREATED
        invoice_number = res.data["data"]["invoice_number"]

        # Detail
        detail_url = reverse("analytics:invoice_detail", args=[invoice_number])
        res = api_client.get(detail_url)
        assert res.status_code == http_status.HTTP_200_OK

        # Download PDF
        dl_url = reverse("analytics:invoice_download", args=[invoice_number])
        res = api_client.get(dl_url)
        assert res.status_code == http_status.HTTP_200_OK
        assert res["Content-Type"] == "application/pdf"

        # Regenerate
        regen_url = reverse("analytics:invoice_regenerate", args=[invoice_number])
        res = api_client.post(regen_url)
        assert res.status_code == http_status.HTTP_200_OK

    def test_invoice_list_api(self, api_client):
        _, merchant, customer = _setup_merchant_and_auth(api_client)
        order = _create_order(merchant, customer, "3000.00")
        InvoiceService.create_invoice(order)

        url = reverse("analytics:invoice_list")
        res = api_client.get(url, {"merchant_id": str(merchant.id)})
        assert res.status_code == http_status.HTTP_200_OK


# ══════════════════════════════════════════════════════════
# BONUS ENDPOINTS TESTS
# ══════════════════════════════════════════════════════════
@pytest.mark.django_db
class TestBonusEndpoints:
    def test_health_check(self, api_client):
        res = api_client.get(reverse("health-check"))
        assert res.status_code == http_status.HTTP_200_OK
        assert res.data["data"]["status"] in ("healthy", "degraded")

    def test_readiness_check(self, api_client):
        res = api_client.get(reverse("readiness-check"))
        assert res.status_code == http_status.HTTP_200_OK
        assert res.data["data"]["ready"] is True

    def test_liveness_check(self, api_client):
        res = api_client.get(reverse("liveness-check"))
        assert res.status_code == http_status.HTTP_200_OK
        assert res.data["data"]["alive"] is True

    def test_version_info(self, api_client):
        res = api_client.get(reverse("version-info"))
        assert res.status_code == http_status.HTTP_200_OK
        assert "version" in res.data["data"]
        assert "python_version" in res.data["data"]
