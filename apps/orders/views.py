from common.pagination import StandardResultsSetPagination
from common.response import APIResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from merchant.services.merchant_service import MerchantService
from orders.repositories.order_repository import OrderRepository
from orders.serializers import OrderCreateSerializer, OrderSerializer
from orders.services.order_service import OrderService
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List Orders",
        description="Returns paginated orders. Merchants see all their orders; Customers see their own orders.",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by Order Status",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="customer_id",
                description="Filter by Customer ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="search",
                description="Search by order number or description",
                required=False,
                type=str,
            ),
        ],
        responses={200: OrderSerializer(many=True)},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        status_param = request.query_params.get("status")
        customer_id = request.query_params.get("customer_id")
        search = request.query_params.get("search")

        queryset = OrderRepository.list_orders_queryset(
            merchant=merchant,
            status=status_param,
            customer_id=customer_id,
            search_query=search,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create Order",
        description="Creates a new order intent in PENDING state.",
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
    )
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = OrderService.create_order(request.user, serializer.validated_data)
        return APIResponse.success(
            data=OrderSerializer(order).data,
            message="Order created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Order Details",
        description="Returns details of an order by UUID or order number (`ord_...`).",
        responses={200: OrderSerializer},
    )
    def get(self, request, order_identifier):
        order = OrderService.get_order(request.user, order_identifier)
        return APIResponse.success(
            data=OrderSerializer(order).data,
            message="Order retrieved successfully.",
        )


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cancel Order",
        description="Transitions an order from PENDING/PROCESSING/DRAFT to CANCELLED state.",
        responses={200: OrderSerializer},
    )
    def post(self, request, order_identifier):
        order = OrderService.cancel_order(request.user, order_identifier)
        return APIResponse.success(
            data=OrderSerializer(order).data,
            message="Order cancelled successfully.",
        )


class OrderExpireView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Manually Expire Order",
        description="Transitions a PENDING order to EXPIRED state.",
        responses={200: OrderSerializer},
    )
    def post(self, request, order_identifier):
        order = OrderService.expire_order(request.user, order_identifier)
        return APIResponse.success(
            data=OrderSerializer(order).data,
            message="Order expired successfully.",
        )
