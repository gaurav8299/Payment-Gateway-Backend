import secrets
import string
from typing import Any, Dict, Tuple

from accounts.models import User
from accounts.repositories.user_repository import UserRepository
from accounts.tasks import send_password_reset_email_task, send_verification_email_task
from common.exceptions import BusinessLogicError, ResourceNotFoundError
from common.services.redis_service import RedisService
from common.utils import generate_unique_id
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class AuthService:
    """
    Service layer executing authentication and user account management logic.
    """

    @staticmethod
    def generate_otp() -> str:
        return "".join(secrets.choice(string.digits) for _ in range(6))

    @classmethod
    def register_user(cls, validated_data: Dict[str, Any]) -> User:
        email = validated_data["email"].lower()
        if UserRepository.exists_by_email(email):
            raise BusinessLogicError(
                detail="A user with this email address already exists.",
                code="EMAIL_EXISTS",
            )

        user = UserRepository.create_user(
            email=email,
            password=validated_data["password"],
            role=validated_data.get("role"),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone_number=validated_data.get("phone_number"),
        )

        # Generate & store 6-digit verification OTP in Redis (5 min TTL)
        otp = cls.generate_otp()
        RedisService.set_otp(email, otp, timeout=300)

        # Dispatch async verification email task
        send_verification_email_task.delay(email, otp)

        return user

    @classmethod
    def login_user(cls, email: str, password: str) -> Tuple[User, Dict[str, str]]:
        email = email.lower()
        user = UserRepository.get_by_email(email)

        if not user or not user.check_password(password):
            raise BusinessLogicError(
                detail="Invalid email or password.", code="INVALID_CREDENTIALS"
            )

        if not user.is_active:
            raise BusinessLogicError(
                detail="Account is disabled.", code="ACCOUNT_DISABLED"
            )

        # Generate SimpleJWT tokens
        refresh = RefreshToken.for_user(user)
        # Custom claims
        refresh["role"] = user.role
        refresh["email"] = user.email

        tokens = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        return user, tokens

    @classmethod
    def refresh_tokens(cls, refresh_token_str: str) -> Dict[str, str]:
        try:
            refresh = RefreshToken(refresh_token_str)
            data = {
                "access": str(refresh.access_token),
            }
            # If token rotation is enabled in SimpleJWT
            if getattr(refresh, "outstandings", None):
                refresh.set_jti()
                refresh.set_exp()
                data["refresh"] = str(refresh)
            return data
        except TokenError as e:
            raise BusinessLogicError(
                detail=f"Invalid or expired refresh token: {str(e)}",
                code="INVALID_TOKEN",
            )

    @classmethod
    def logout_user(cls, refresh_token_str: str) -> bool:
        try:
            token = RefreshToken(refresh_token_str)
            token.blacklist()
            return True
        except TokenError:
            raise BusinessLogicError(
                detail="Invalid or already blacklisted refresh token.",
                code="INVALID_TOKEN",
            )

    @classmethod
    def verify_email_otp(cls, email: str, otp: str) -> bool:
        email = email.lower()
        user = UserRepository.get_by_email(email)
        if not user:
            raise ResourceNotFoundError(detail="User account not found.")

        if user.is_email_verified:
            return True

        stored_otp = RedisService.get_otp(email)
        attempts = RedisService.get_otp_attempts(email)

        if attempts >= 3:
            RedisService.delete_otp(email)
            raise BusinessLogicError(
                detail="Maximum OTP verification attempts exceeded. Please request a new OTP.",
                code="OTP_LIMIT_EXCEEDED",
            )

        if not stored_otp or stored_otp != otp:
            RedisService.increment_otp_attempts(email)
            raise BusinessLogicError(
                detail="Invalid or expired verification OTP.", code="INVALID_OTP"
            )

        # Mark email verified and clear Redis state
        UserRepository.set_email_verified(user, True)
        RedisService.delete_otp(email)
        return True

    @classmethod
    def resend_verification_otp(cls, email: str) -> bool:
        email = email.lower()
        user = UserRepository.get_by_email(email)
        if not user:
            # Prevent user enumeration by returning True silently
            return True

        if user.is_email_verified:
            raise BusinessLogicError(
                detail="Email address is already verified.", code="ALREADY_VERIFIED"
            )

        otp = cls.generate_otp()
        RedisService.set_otp(email, otp, timeout=300)
        send_verification_email_task.delay(email, otp)
        return True

    @classmethod
    def request_password_reset(cls, email: str) -> bool:
        email = email.lower()
        user = UserRepository.get_by_email(email)
        if not user:
            # Prevent user enumeration: always return success
            return True

        reset_token = generate_unique_id("rst", length=32)
        RedisService.set_reset_token(email, reset_token, timeout=900)

        # Dispatch async password reset email task
        send_password_reset_email_task.delay(email, reset_token)
        return True

    @classmethod
    def reset_password(cls, email: str, reset_token: str, new_password: str) -> bool:
        email = email.lower()
        user = UserRepository.get_by_email(email)
        if not user:
            raise ResourceNotFoundError(detail="User account not found.")

        stored_token = RedisService.get_reset_token(email)
        if not stored_token or stored_token != reset_token:
            raise BusinessLogicError(
                detail="Invalid or expired password reset token.",
                code="INVALID_RESET_TOKEN",
            )

        UserRepository.set_password(user, new_password)
        RedisService.delete_reset_token(email)
        return True
