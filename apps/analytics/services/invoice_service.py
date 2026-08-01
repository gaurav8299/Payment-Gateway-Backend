import io
import logging
import uuid
from decimal import Decimal

from orders.models import Invoice, InvoiceStatus, Order
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("payment_gateway")


class InvoiceService:
    """
    Service for generating, retrieving, and managing PDF invoices.
    Uses ReportLab for high-quality PDF rendering.
    """

    @staticmethod
    def generate_invoice_number() -> str:
        return f"inv_{uuid.uuid4().hex[:24]}"

    @staticmethod
    def create_invoice(order: Order) -> Invoice:
        """Create an Invoice record from an Order."""
        tax_rate = Decimal("0.18")  # 18% GST default
        subtotal = order.amount
        tax_amount = (subtotal * tax_rate).quantize(Decimal("0.01"))
        total_amount = subtotal + tax_amount

        invoice = Invoice.objects.create(
            invoice_number=InvoiceService.generate_invoice_number(),
            order=order,
            merchant=order.merchant,
            customer=order.customer,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency=order.currency,
            status=InvoiceStatus.ISSUED,
        )
        logger.info(
            f"Invoice {invoice.invoice_number} created for order {order.order_number}"
        )
        return invoice

    @staticmethod
    def generate_pdf(invoice: Invoice) -> bytes:
        """
        Generate a professional PDF invoice using ReportLab.
        Returns raw PDF bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )
        styles = getSampleStyleSheet()
        story = []

        # ── Custom Styles ──────────────────────────
        title_style = ParagraphStyle(
            "InvoiceTitle",
            parent=styles["Title"],
            fontSize=24,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#16213e"),
            spaceBefore=12,
            spaceAfter=6,
        )
        normal_style = styles["Normal"]
        bold_style = ParagraphStyle(
            "Bold", parent=normal_style, fontName="Helvetica-Bold"
        )

        # ── Header ─────────────────────────────────
        story.append(Paragraph("INVOICE", title_style))
        story.append(Paragraph(f"Invoice #: {invoice.invoice_number}", normal_style))
        story.append(
            Paragraph(f"Date: {invoice.created_at.strftime('%B %d, %Y')}", normal_style)
        )
        story.append(Paragraph(f"Status: {invoice.status}", normal_style))
        story.append(Spacer(1, 12))
        story.append(
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0"))
        )
        story.append(Spacer(1, 12))

        # ── Merchant Details ───────────────────────
        merchant = invoice.merchant
        story.append(Paragraph("From (Merchant)", heading_style))
        story.append(Paragraph(f"{merchant.business_name}", bold_style))
        story.append(Paragraph(f"{merchant.support_email}", normal_style))
        story.append(Paragraph(f"{merchant.support_phone}", normal_style))
        if merchant.gst_number:
            story.append(Paragraph(f"GST: {merchant.gst_number}", normal_style))
        story.append(Spacer(1, 8))

        # ── Customer Details ───────────────────────
        customer = invoice.customer
        if customer:
            story.append(Paragraph("To (Customer)", heading_style))
            story.append(Paragraph(f"{customer.name}", bold_style))
            story.append(Paragraph(f"{customer.email}", normal_style))
            if customer.phone:
                story.append(Paragraph(f"{customer.phone}", normal_style))
            story.append(Spacer(1, 8))

        # ── Order Details ──────────────────────────
        order = invoice.order
        story.append(Paragraph("Order Details", heading_style))
        order_data = [
            ["Field", "Value"],
            ["Order Number", order.order_number],
            ["Description", order.description or "N/A"],
            ["Currency", order.currency],
            ["Status", order.status],
        ]
        order_table = Table(order_data, colWidths=[2.5 * inch, 4 * inch])
        order_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f5f5f5")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(order_table)
        story.append(Spacer(1, 16))

        # ── Financial Summary ──────────────────────
        story.append(Paragraph("Financial Summary", heading_style))
        fin_data = [
            ["Item", "Amount"],
            ["Subtotal", f"{invoice.currency} {invoice.subtotal}"],
            ["Discount", f"{invoice.currency} {invoice.discount_amount}"],
            ["Tax (GST 18%)", f"{invoice.currency} {invoice.tax_amount}"],
            ["Total", f"{invoice.currency} {invoice.total_amount}"],
        ]
        fin_table = Table(fin_data, colWidths=[4 * inch, 2.5 * inch])
        fin_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f5f5f5")],
                    ),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(fin_table)
        story.append(Spacer(1, 24))

        # ── Terms & Conditions ─────────────────────
        story.append(
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0"))
        )
        story.append(Spacer(1, 8))
        story.append(Paragraph("Terms & Conditions", heading_style))
        story.append(
            Paragraph(
                "1. Payment is due within 30 days of invoice date.<br/>"
                "2. Refund requests must be filed within 7 business days.<br/>"
                "3. This is a computer-generated invoice and does not require a signature.",
                normal_style,
            )
        )

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(
            f"PDF generated for invoice {invoice.invoice_number} ({len(pdf_bytes)} bytes)"
        )
        return pdf_bytes

    @staticmethod
    def get_invoice_by_id(invoice_number: str):
        try:
            return Invoice.objects.select_related("order", "merchant", "customer").get(
                invoice_number=invoice_number
            )
        except Invoice.DoesNotExist:
            return None

    @staticmethod
    def list_invoices(merchant_id: str = None):
        qs = Invoice.objects.select_related("order", "merchant", "customer").all()
        if merchant_id:
            qs = qs.filter(merchant_id=merchant_id)
        return qs
