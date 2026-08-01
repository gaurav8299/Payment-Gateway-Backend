from common.pagination import StandardResultsSetPagination
from common.response import APIResponse
from drf_spectacular.utils import extend_schema
from merchant.services.merchant_service import MerchantService
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from webhooks.repositories.webhook_repository import WebhookRepository
from webhooks.serializers import (
    WebhookDeliverySerializer,
    WebhookEndpointCreateSerializer,
    WebhookEndpointSerializer,
    WebhookEventSerializer,
)
from webhooks.services.webhook_service import WebhookService


class WebhookEndpointListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List Webhook Endpoints",
        description="Returns list of configured webhook receiver endpoints for merchant.",
        responses={200: WebhookEndpointSerializer(many=True)},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        queryset = WebhookRepository.list_endpoints(merchant)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = WebhookEndpointSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create Webhook Endpoint",
        description="Configures a new HTTPS webhook destination and returns the raw secret key ONCE (`whsec_...`).",
        request=WebhookEndpointCreateSerializer,
        responses={201: dict},
    )
    def post(self, request):
        serializer = WebhookEndpointCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        endpoint, raw_secret = WebhookService.create_endpoint(
            request.user, serializer.validated_data
        )
        data = WebhookEndpointSerializer(endpoint).data
        data["secret_key"] = raw_secret  # Shown ONLY ONCE!
        return APIResponse.success(
            data=data,
            message="Webhook endpoint created successfully. Store secret_key securely.",
            status_code=status.HTTP_201_CREATED,
        )


class WebhookEndpointDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Endpoint Details",
        responses={200: WebhookEndpointSerializer},
    )
    def get(self, request, endpoint_id):
        endpoint = WebhookService.get_endpoint(request.user, endpoint_id)
        return APIResponse.success(
            data=WebhookEndpointSerializer(endpoint).data,
            message="Webhook endpoint retrieved successfully.",
        )

    @extend_schema(
        summary="Delete Endpoint",
        responses={200: dict},
    )
    def delete(self, request, endpoint_id):
        endpoint = WebhookService.get_endpoint(request.user, endpoint_id)
        endpoint.delete()
        return APIResponse.success(message="Webhook endpoint deleted successfully.")


class WebhookSecretRotateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Rotate Webhook Secret",
        description="Generates a new HMAC secret key for webhook endpoint signature verification.",
        responses={200: dict},
    )
    def post(self, request, endpoint_id):
        new_secret = WebhookService.rotate_secret(request.user, endpoint_id)
        return APIResponse.success(
            data={"new_secret_key": new_secret},
            message="Webhook secret rotated successfully. Update your signature verification code.",
        )


class WebhookEventListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List Webhook Events",
        description="Returns paginated domain event logs generated for webhooks.",
        responses={200: WebhookEventSerializer(many=True)},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        queryset = WebhookRepository.list_events(merchant)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = WebhookEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class WebhookDeliveryListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        summary="List Webhook Delivery Attempts",
        description="Returns audit log of all HTTP webhook delivery attempts.",
        responses={200: WebhookDeliverySerializer(many=True)},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        queryset = WebhookRepository.list_deliveries(merchant)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = WebhookDeliverySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class WebhookReplayView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Replay Webhook Delivery",
        description="Re-dispatches a webhook delivery attempt for an event.",
        responses={200: WebhookDeliverySerializer},
    )
    def post(self, request, delivery_id):
        new_delivery = WebhookService.replay_delivery(request.user, delivery_id)
        return APIResponse.success(
            data=WebhookDeliverySerializer(new_delivery).data,
            message="Webhook delivery replay queued successfully.",
        )


class WebhookTestPingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Send Test Ping Event",
        description="Publishes a mock test ping event to test webhook delivery and signature verification.",
        responses={200: dict},
    )
    def post(self, request, endpoint_id):
        res = WebhookService.send_test_event(request.user, endpoint_id)
        return APIResponse.success(
            data=res,
            message="Test webhook ping event published successfully.",
        )
