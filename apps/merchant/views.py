from accounts.permissions import IsMerchantPermission
from common.response import APIResponse
from drf_spectacular.utils import extend_schema
from merchant.serializers import (
    CreateAPIKeySerializer,
    MerchantAPIKeySerializer,
    MerchantProfileSerializer,
    MerchantProfileUpdateSerializer,
    WebhookEndpointSerializer,
)
from merchant.services.merchant_service import MerchantService
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class MerchantProfileView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]
    serializer_class = MerchantProfileSerializer

    @extend_schema(
        summary="Get Merchant Profile",
        description="Returns details of the merchant profile associated with authenticated user.",
        responses={200: MerchantProfileSerializer},
    )
    def get(self, request):
        merchant = MerchantService.get_or_create_profile(request.user)
        serializer = self.serializer_class(merchant)
        return APIResponse.success(
            data=serializer.data,
            message="Merchant profile retrieved successfully.",
        )

    @extend_schema(
        summary="Update Merchant Profile",
        description="Updates business details, GSTIN, PAN, address, currency, or support contacts.",
        request=MerchantProfileUpdateSerializer,
        responses={200: MerchantProfileSerializer},
    )
    def patch(self, request):
        serializer = MerchantProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        merchant = MerchantService.update_profile(
            request.user, serializer.validated_data
        )
        profile_data = MerchantProfileSerializer(merchant).data
        return APIResponse.success(
            data=profile_data,
            message="Merchant profile updated successfully.",
        )


class MerchantStatsView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Merchant Statistics & Revenue Dashboard",
        description="Returns summary statistics, daily revenue, and transaction volume aggregates.",
        responses={200: dict},
    )
    def get(self, request):
        stats = MerchantService.get_merchant_stats(request.user)
        return APIResponse.success(
            data=stats,
            message="Merchant statistics retrieved successfully.",
        )


class MerchantAPIKeyListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="List Active API Keys",
        description="Lists active Publishable and Secret key prefixes for authenticated merchant.",
        responses={200: MerchantAPIKeySerializer(many=True)},
    )
    def get(self, request):
        keys = MerchantService.list_api_keys(request.user)
        serializer = MerchantAPIKeySerializer(keys, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="API keys retrieved successfully.",
        )

    @extend_schema(
        summary="Generate API Keys",
        description="Generates new Publishable (`pk_live_...`) and Secret (`sk_live_...`) key pair. The raw Secret Key is returned ONLY ONCE.",
        request=CreateAPIKeySerializer,
        responses={201: dict},
    )
    def post(self, request):
        serializer = CreateAPIKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key_obj, raw_secret_key = MerchantService.generate_api_key(
            request.user, serializer.validated_data.get("name", "Default Live Key")
        )
        key_data = MerchantAPIKeySerializer(key_obj).data
        key_data["secret_key"] = raw_secret_key  # Returned ONLY ONCE!

        return APIResponse.success(
            data=key_data,
            message="API Key generated successfully. Please save the secret_key securely as it will NOT be shown again.",
            status_code=status.HTTP_201_CREATED,
        )


class MerchantAPIKeyRevokeView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Revoke API Key",
        description="Deactivates an API key pair.",
        responses={200: dict},
    )
    def post(self, request, key_id):
        MerchantService.revoke_api_key(request.user, key_id)
        return APIResponse.success(
            data={},
            message="API Key revoked successfully.",
        )


class WebhookSecretRotateView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]

    @extend_schema(
        summary="Rotate Webhook HMAC Signing Secret",
        description="Generates or rotates merchant Webhook signing secret (`whsec_...`). The raw secret is returned ONLY ONCE.",
        responses={200: dict},
    )
    def post(self, request):
        raw_secret = MerchantService.rotate_webhook_secret(request.user)
        return APIResponse.success(
            data={"webhook_secret": raw_secret},
            message="Webhook secret generated/rotated successfully. Please save it securely.",
        )


class WebhookEndpointListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]
    serializer_class = WebhookEndpointSerializer

    @extend_schema(
        summary="List Webhook Endpoints",
        description="Returns all registered webhook callback endpoints for merchant.",
        responses={200: WebhookEndpointSerializer(many=True)},
    )
    def get(self, request):
        endpoints = MerchantService.list_webhook_endpoints(request.user)
        serializer = self.serializer_class(endpoints, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="Webhook endpoints retrieved successfully.",
        )

    @extend_schema(
        summary="Create Webhook Endpoint",
        description="Registers a new callback URL and event subscriptions.",
        request=WebhookEndpointSerializer,
        responses={201: WebhookEndpointSerializer},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        endpoint = MerchantService.create_webhook_endpoint(
            user=request.user,
            url=serializer.validated_data["url"],
            enabled_events=serializer.validated_data["enabled_events"],
            description=serializer.validated_data.get("description", ""),
        )
        return APIResponse.success(
            data=self.serializer_class(endpoint).data,
            message="Webhook endpoint created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class WebhookEndpointDetailView(APIView):
    permission_classes = [IsAuthenticated, IsMerchantPermission]
    serializer_class = WebhookEndpointSerializer

    @extend_schema(
        summary="Update Webhook Endpoint",
        description="Updates callback URL or enabled event subscriptions.",
        request=WebhookEndpointSerializer,
        responses={200: WebhookEndpointSerializer},
    )
    def patch(self, request, endpoint_id):
        serializer = self.serializer_class(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        endpoint = MerchantService.update_webhook_endpoint(
            request.user, endpoint_id, serializer.validated_data
        )
        return APIResponse.success(
            data=self.serializer_class(endpoint).data,
            message="Webhook endpoint updated successfully.",
        )

    @extend_schema(
        summary="Delete Webhook Endpoint",
        description="Removes a webhook callback endpoint.",
        responses={200: dict},
    )
    def delete(self, request, endpoint_id):
        MerchantService.delete_webhook_endpoint(request.user, endpoint_id)
        return APIResponse.success(
            data={},
            message="Webhook endpoint deleted successfully.",
        )
