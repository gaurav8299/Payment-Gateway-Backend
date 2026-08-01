from accounts.repositories.user_repository import UserRepository
from accounts.serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    ResendOTPSerializer,
    ResetPasswordSerializer,
    TokenRefreshSerializer,
    UserProfileSerializer,
    VerifyEmailOTPSerializer,
)
from accounts.services.auth_service import AuthService
from common.response import APIResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(
        summary="User Registration",
        description="Registers a new user (Customer, Merchant, or Admin) and sends a 6-digit verification OTP to their email address.",
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="User registered successfully. Check email for verification OTP."
            ),
            400: OpenApiResponse(description="Validation error or duplicate email."),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.register_user(serializer.validated_data)
        profile_data = UserProfileSerializer(user).data
        return APIResponse.success(
            data=profile_data,
            message="User registered successfully. A verification OTP has been sent to your email.",
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(
        summary="User JWT Login",
        description="Authenticates user credentials and returns JWT Access and Refresh tokens.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful. JWT tokens returned."),
            400: OpenApiResponse(description="Invalid email or password."),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user, tokens = AuthService.login_user(email, password)
        user_data = UserProfileSerializer(user).data

        return APIResponse.success(
            data={"user": user_data, "tokens": tokens},
            message="Login successful.",
            status_code=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        summary="JWT Token Refresh",
        description="Generates a new JWT access token using a valid refresh token.",
        request=TokenRefreshSerializer,
        responses={
            200: OpenApiResponse(description="New JWT access token generated."),
            400: OpenApiResponse(description="Invalid or blacklisted refresh token."),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = AuthService.refresh_tokens(serializer.validated_data["refresh"])
        return APIResponse.success(
            data=tokens,
            message="Token refreshed successfully.",
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        summary="User Logout & Token Blacklist",
        description="Blacklists the provided refresh token, invalidating session.",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(
                description="Logout successful. Refresh token blacklisted."
            ),
            400: OpenApiResponse(description="Invalid refresh token."),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.logout_user(serializer.validated_data["refresh"])
        return APIResponse.success(
            data={},
            message="Logged out successfully.",
        )


class VerifyEmailOTPView(APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyEmailOTPSerializer

    @extend_schema(
        summary="Verify Email OTP",
        description="Verifies the 6-digit OTP code sent to user email and marks email as verified.",
        request=VerifyEmailOTPSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully."),
            400: OpenApiResponse(
                description="Invalid OTP or maximum attempt limit exceeded."
            ),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.verify_email_otp(
            serializer.validated_data["email"],
            serializer.validated_data["otp"],
        )
        return APIResponse.success(
            data={},
            message="Email address verified successfully.",
        )


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResendOTPSerializer

    @extend_schema(
        summary="Resend Verification OTP",
        description="Resends a new verification OTP to the user email if not yet verified.",
        request=ResendOTPSerializer,
        responses={
            200: OpenApiResponse(description="Verification OTP resent successfully."),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.resend_verification_otp(serializer.validated_data["email"])
        return APIResponse.success(
            data={},
            message="If an unverified account exists with that email, a new verification OTP has been sent.",
        )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    @extend_schema(
        summary="Forgot Password Request",
        description="Requests a password reset token to be emailed to the user. Prevents user enumeration.",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset email dispatched."),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.request_password_reset(serializer.validated_data["email"])
        return APIResponse.success(
            data={},
            message="If an account exists with that email, a password reset link/token has been sent.",
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    @extend_schema(
        summary="Reset Password",
        description="Resets the user's password using a valid reset token.",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully."),
            400: OpenApiResponse(
                description="Invalid token or non-matching passwords."
            ),
        },
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password(
            serializer.validated_data["email"],
            serializer.validated_data["reset_token"],
            serializer.validated_data["new_password"],
        )
        return APIResponse.success(
            data={},
            message="Password reset successfully. You can now login with your new password.",
        )


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(
        summary="Get Current User Profile",
        description="Returns details of the currently authenticated user.",
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        serializer = self.serializer_class(request.user)
        return APIResponse.success(
            data=serializer.data,
            message="Profile retrieved successfully.",
        )

    @extend_schema(
        summary="Update Current User Profile",
        description="Updates first name, last name, or phone number of current user.",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request):
        user = UserRepository.update_user(
            request.user,
            first_name=request.data.get("first_name"),
            last_name=request.data.get("last_name"),
            phone_number=request.data.get("phone_number"),
        )
        serializer = self.serializer_class(user)
        return APIResponse.success(
            data=serializer.data,
            message="Profile updated successfully.",
        )
