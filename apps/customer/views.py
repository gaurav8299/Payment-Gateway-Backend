from accounts.permissions import IsMerchantPermission
from common.pagination import StandardResultsSetPagination
from common.response import APIResponse
from customer.repositories.customer_repository import CustomerRepository
from customer.serializers import (
    AddMockPaymentMethodSerializer,
    CustomerCreateUpdateSerializer,
    CustomerSerializer,
    SavedPaymentMethodSerializer,
)
from customer.services.customer_service import CustomerService
from drf_spectacular.utils import OpenApiParameter, extend_schema
from merchant.services.merchant_service import MerchantService
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class CustomerListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List & Search Customers",
        description="Returns paginated list of customers belonging to authenticated merchant. Supports search by name, email, or phone.",
        parameters=[
            OpenApiParameter(
                name="search",
                description="Search query string",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="page", description="Page number", required=False, type=int
            ),
            OpenApiParameter(
                name="page_size", description="Page size", required=False, type=int
            ),
        ],
        responses={200: CustomerSerializer(many=True)},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        search_query = request.query_params.get("search")
        queryset = CustomerRepository.list_customers_queryset(merchant, search_query)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CustomerSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create Customer",
        description="Creates a new customer profile associated with authenticated merchant.",
        request=CustomerCreateUpdateSerializer,
        responses={201: CustomerSerializer},
    )
    def post(self, request):
        serializer = CustomerCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = CustomerService.create_customer(
            request.user, serializer.validated_data
        )
        return APIResponse.success(
            data=CustomerSerializer(customer).data,
            message="Customer created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Get Customer Details",
        description="Retrieves details of a specific customer by ID.",
        responses={200: CustomerSerializer},
    )
    def get(self, request, customer_id):
        customer = CustomerService.get_customer(request.user, customer_id)
        return APIResponse.success(
            data=CustomerSerializer(customer).data,
            message="Customer retrieved successfully.",
        )

    @extend_schema(
        summary="Update Customer Profile",
        description="Updates name, phone, or metadata of a customer.",
        request=CustomerCreateUpdateSerializer,
        responses={200: CustomerSerializer},
    )
    def patch(self, request, customer_id):
        serializer = CustomerCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        customer = CustomerService.update_customer(
            request.user, customer_id, serializer.validated_data
        )
        return APIResponse.success(
            data=CustomerSerializer(customer).data,
            message="Customer updated successfully.",
        )

    @extend_schema(
        summary="Delete Customer",
        description="Soft deletes a customer entity.",
        responses={200: dict},
    )
    def delete(self, request, customer_id):
        CustomerService.delete_customer(request.user, customer_id)
        return APIResponse.success(
            data={},
            message="Customer deleted successfully.",
        )


class CustomerPaymentMethodListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="List Customer Saved Payment Methods",
        description="Returns tokenized saved cards, UPI IDs, or Wallets for customer.",
        responses={200: SavedPaymentMethodSerializer(many=True)},
    )
    def get(self, request, customer_id):
        methods = CustomerService.list_payment_methods(request.user, customer_id)
        serializer = SavedPaymentMethodSerializer(methods, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="Saved payment methods retrieved successfully.",
        )

    @extend_schema(
        summary="Add Saved Payment Method (Mock Tokenization)",
        description="Tokenizes a card, UPI ID, or Wallet. Raw card numbers are NEVER stored.",
        request=AddMockPaymentMethodSerializer,
        responses={201: SavedPaymentMethodSerializer},
    )
    def post(self, request, customer_id):
        serializer = AddMockPaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pm = CustomerService.add_mock_payment_method(
            request.user, customer_id, serializer.validated_data
        )
        return APIResponse.success(
            data=SavedPaymentMethodSerializer(pm).data,
            message="Payment method tokenized and saved successfully.",
            status_code=status.HTTP_201_CREATED,
        )
