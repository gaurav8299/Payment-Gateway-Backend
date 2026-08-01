import logging
from decimal import ROUND_HALF_UP, Decimal

from common.exceptions import BusinessLogicError, ResourceNotFoundError
from orders.models import Coupon, CouponDiscountType, CouponStatus

logger = logging.getLogger("payment_gateway")


class CouponService:
    """
    Service for creating, validating, and applying coupons.
    Encapsulates all business logic for the coupon lifecycle.
    """

    @staticmethod
    def create_coupon(merchant_id: str, data: dict) -> Coupon:
        code = data["code"].upper()
        if Coupon.objects.filter(code=code).exists():
            raise BusinessLogicError(detail=f"Coupon code '{code}' already exists.")

        coupon = Coupon.objects.create(
            code=code,
            merchant_id=merchant_id,
            discount_type=data.get("discount_type", CouponDiscountType.PERCENTAGE),
            discount_value=Decimal(str(data["discount_value"])),
            max_discount_amount=(
                Decimal(str(data["max_discount_amount"]))
                if data.get("max_discount_amount")
                else None
            ),
            min_order_amount=Decimal(str(data.get("min_order_amount", "0.00"))),
            usage_limit=data.get("usage_limit", 100),
        )
        logger.info(f"Coupon {coupon.code} created for merchant {merchant_id}")
        return coupon

    @staticmethod
    def validate_coupon(
        code: str, order_amount: Decimal, merchant_id: str = None
    ) -> dict:
        """
        Validate a coupon code and return the discount breakdown.
        Does NOT consume usage – use apply_coupon for that.
        """
        try:
            coupon = Coupon.objects.get(code=code.upper())
        except Coupon.DoesNotExist:
            raise ResourceNotFoundError(detail=f"Coupon '{code}' not found.")

        # Business validations
        if coupon.status != CouponStatus.ACTIVE:
            raise BusinessLogicError(detail=f"Coupon '{code}' is {coupon.status}.")

        if merchant_id and str(coupon.merchant_id) != str(merchant_id):
            raise BusinessLogicError(detail="Coupon does not belong to this merchant.")

        if coupon.used_count >= coupon.usage_limit:
            raise BusinessLogicError(detail="Coupon usage limit exceeded.")

        if order_amount < coupon.min_order_amount:
            raise BusinessLogicError(
                detail=f"Minimum order amount for this coupon is {coupon.min_order_amount}."
            )

        # Calculate discount
        discount = CouponService._calculate_discount(coupon, order_amount)

        return {
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": str(coupon.discount_value),
            "calculated_discount": str(discount),
            "final_amount": str(order_amount - discount),
            "valid": True,
        }

    @staticmethod
    def apply_coupon(code: str, order_amount: Decimal, merchant_id: str = None) -> dict:
        """
        Apply a coupon – validates, calculates discount, and increments used_count.
        """
        validation = CouponService.validate_coupon(code, order_amount, merchant_id)

        coupon = Coupon.objects.get(code=code.upper())
        coupon.used_count += 1
        coupon.save(update_fields=["used_count"])
        logger.info(f"Coupon {coupon.code} applied. Used count: {coupon.used_count}")

        return validation

    @staticmethod
    def _calculate_discount(coupon: Coupon, order_amount: Decimal) -> Decimal:
        if coupon.discount_type == CouponDiscountType.PERCENTAGE:
            discount = (order_amount * coupon.discount_value / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if coupon.max_discount_amount and discount > coupon.max_discount_amount:
                discount = coupon.max_discount_amount
        else:
            discount = coupon.discount_value

        # Discount can never exceed order amount
        if discount > order_amount:
            discount = order_amount

        return discount

    @staticmethod
    def update_coupon(coupon_id: str, data: dict) -> Coupon:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
        except Coupon.DoesNotExist:
            raise ResourceNotFoundError(detail="Coupon not found.")

        for field in (
            "discount_value",
            "max_discount_amount",
            "min_order_amount",
            "usage_limit",
            "status",
        ):
            if field in data:
                setattr(coupon, field, data[field])
        coupon.save()
        logger.info(f"Coupon {coupon.code} updated")
        return coupon

    @staticmethod
    def delete_coupon(coupon_id: str):
        try:
            coupon = Coupon.objects.get(id=coupon_id)
        except Coupon.DoesNotExist:
            raise ResourceNotFoundError(detail="Coupon not found.")

        coupon.status = CouponStatus.DISABLED
        coupon.save(update_fields=["status"])
        logger.info(f"Coupon {coupon.code} disabled")
        return coupon
