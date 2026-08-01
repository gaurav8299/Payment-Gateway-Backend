from typing import List, Optional
from uuid import UUID

from customer.models import CustomerProfile, SavedPaymentMethod
from django.db.models import Q, QuerySet
from merchant.models import MerchantProfile


class CustomerRepository:
    """
    Repository for Customer data operations with strict Merchant Isolation controls.
    """

    @staticmethod
    def get_by_id(
        customer_id: UUID | str, merchant: MerchantProfile
    ) -> Optional[CustomerProfile]:
        try:
            return CustomerProfile.objects.get(id=customer_id, merchant=merchant)
        except CustomerProfile.DoesNotExist:
            return None

    @staticmethod
    def get_by_email(
        email: str, merchant: MerchantProfile
    ) -> Optional[CustomerProfile]:
        try:
            return CustomerProfile.objects.get(email__iexact=email, merchant=merchant)
        except CustomerProfile.DoesNotExist:
            return None

    @staticmethod
    def create_customer(
        merchant: MerchantProfile,
        name: str,
        email: str,
        phone: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> CustomerProfile:
        return CustomerProfile.objects.create(
            merchant=merchant,
            name=name,
            email=email.lower(),
            phone=phone,
            metadata=metadata or {},
        )

    @staticmethod
    def update_customer(customer: CustomerProfile, **kwargs) -> CustomerProfile:
        for attr, value in kwargs.items():
            if hasattr(customer, attr) and value is not None:
                setattr(customer, attr, value)
        customer.save()
        return customer

    @staticmethod
    def delete_customer(customer_id: UUID | str, merchant: MerchantProfile) -> bool:
        try:
            customer = CustomerProfile.objects.get(id=customer_id, merchant=merchant)
            customer.delete()
            return True
        except CustomerProfile.DoesNotExist:
            return False

    @staticmethod
    def list_customers_queryset(
        merchant: MerchantProfile, search_query: Optional[str] = None
    ) -> QuerySet:
        qs = CustomerProfile.objects.filter(merchant=merchant)
        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone__icontains=search_query)
            )
        return qs

    @staticmethod
    def create_saved_payment_method(
        customer: CustomerProfile,
        type: str,
        card_token: str,
        masked_card_number: str = "",
        card_brand: str = "VISA",
        exp_month: Optional[int] = None,
        exp_year: Optional[int] = None,
        fingerprint: str = "",
        upi_id: Optional[str] = None,
        wallet_provider: Optional[str] = None,
        is_default: bool = False,
    ) -> SavedPaymentMethod:
        if is_default:
            SavedPaymentMethod.objects.filter(customer=customer).update(
                is_default=False
            )

        return SavedPaymentMethod.objects.create(
            customer=customer,
            type=type,
            card_token=card_token,
            masked_card_number=masked_card_number,
            card_brand=card_brand,
            exp_month=exp_month,
            exp_year=exp_year,
            fingerprint=fingerprint,
            upi_id=upi_id,
            wallet_provider=wallet_provider,
            is_default=is_default,
        )

    @staticmethod
    def list_saved_payment_methods(
        customer: CustomerProfile,
    ) -> List[SavedPaymentMethod]:
        return list(SavedPaymentMethod.objects.filter(customer=customer))
