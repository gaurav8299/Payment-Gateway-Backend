from typing import Any, Dict

from accounts.models import User
from common.exceptions import BusinessLogicError, ResourceNotFoundError
from common.utils import generate_unique_id, hash_secret
from customer.models import (
    CardBrand,
    CustomerProfile,
    PaymentMethodType,
    SavedPaymentMethod,
)
from customer.repositories.customer_repository import CustomerRepository
from merchant.services.merchant_service import MerchantService


class CustomerService:
    """
    Service layer for Customer entities and mock payment method tokenization.
    Enforces strict Merchant isolation.
    """

    @classmethod
    def create_customer(
        cls, merchant_user: User, validated_data: Dict[str, Any]
    ) -> CustomerProfile:
        merchant = MerchantService.get_or_create_profile(merchant_user)
        email = validated_data["email"].lower()

        existing = CustomerRepository.get_by_email(email, merchant)
        if existing:
            raise BusinessLogicError(
                detail="A customer with this email address already exists for your merchant account.",
                code="CUSTOMER_EXISTS",
            )

        return CustomerRepository.create_customer(
            merchant=merchant,
            name=validated_data["name"],
            email=email,
            phone=validated_data.get("phone"),
            metadata=validated_data.get("metadata", {}),
        )

    @classmethod
    def get_customer(cls, merchant_user: User, customer_id: str) -> CustomerProfile:
        merchant = MerchantService.get_or_create_profile(merchant_user)
        customer = CustomerRepository.get_by_id(customer_id, merchant)
        if not customer:
            raise ResourceNotFoundError(detail="Customer not found.")
        return customer

    @classmethod
    def update_customer(
        cls, merchant_user: User, customer_id: str, data: Dict[str, Any]
    ) -> CustomerProfile:
        customer = cls.get_customer(merchant_user, customer_id)
        return CustomerRepository.update_customer(customer, **data)

    @classmethod
    def delete_customer(cls, merchant_user: User, customer_id: str) -> bool:
        merchant = MerchantService.get_or_create_profile(merchant_user)
        success = CustomerRepository.delete_customer(customer_id, merchant)
        if not success:
            raise ResourceNotFoundError(detail="Customer not found.")
        return True

    @classmethod
    def add_mock_payment_method(
        cls, merchant_user: User, customer_id: str, validated_data: Dict[str, Any]
    ) -> SavedPaymentMethod:
        customer = cls.get_customer(merchant_user, customer_id)
        method_type = validated_data.get("type", PaymentMethodType.CARD)

        card_token = generate_unique_id("card_token", length=24)

        if method_type == PaymentMethodType.CARD:
            raw_card = validated_data.get("raw_card_number", "4242424242424242")
            masked_card = f"{raw_card[:4]} **** **** {raw_card[-4:]}"
            fingerprint = hash_secret(raw_card)

            return CustomerRepository.create_saved_payment_method(
                customer=customer,
                type=method_type,
                card_token=card_token,
                masked_card_number=masked_card,
                card_brand=validated_data.get("card_brand", CardBrand.VISA),
                exp_month=validated_data.get("exp_month", 12),
                exp_year=validated_data.get("exp_year", 2030),
                fingerprint=fingerprint,
                is_default=validated_data.get("is_default", False),
            )
        elif method_type == PaymentMethodType.UPI:
            return CustomerRepository.create_saved_payment_method(
                customer=customer,
                type=method_type,
                card_token=card_token,
                upi_id=validated_data.get("upi_id", "user@upi"),
                is_default=validated_data.get("is_default", False),
            )
        else:
            return CustomerRepository.create_saved_payment_method(
                customer=customer,
                type=method_type,
                card_token=card_token,
                wallet_provider=validated_data.get("wallet_provider", "PAYTM"),
                is_default=validated_data.get("is_default", False),
            )

    @classmethod
    def list_payment_methods(
        cls, merchant_user: User, customer_id: str
    ) -> list[SavedPaymentMethod]:
        customer = cls.get_customer(merchant_user, customer_id)
        return CustomerRepository.list_saved_payment_methods(customer)
