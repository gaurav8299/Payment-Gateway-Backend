import logging

from django.core.cache import cache

logger = logging.getLogger("payment_gateway")


class RedisService:
    """
    Unified Redis Service providing abstracted access for OTP storage,
    retry limits, idempotency caching, and key-value operations.
    """

    @staticmethod
    def set_otp(identifier: str, otp: str, timeout: int = 300) -> bool:
        """
        Store OTP for an identifier (email/phone) with standard 5-minute TTL.
        """
        key = f"otp:{identifier}"
        return cache.set(key, otp, timeout=timeout)

    @staticmethod
    def get_otp(identifier: str) -> str | None:
        """
        Retrieve OTP stored for an identifier.
        """
        key = f"otp:{identifier}"
        return cache.get(key)

    @staticmethod
    def delete_otp(identifier: str) -> bool:
        """
        Delete OTP for an identifier upon successful verification.
        """
        key = f"otp:{identifier}"
        attempts_key = f"otp_attempts:{identifier}"
        cache.delete(attempts_key)
        return cache.delete(key)

    @staticmethod
    def increment_otp_attempts(identifier: str, timeout: int = 900) -> int:
        """
        Increment incorrect OTP attempts counter. Returns current count.
        """
        key = f"otp_attempts:{identifier}"
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, timeout=timeout)
        return attempts

    @staticmethod
    def get_otp_attempts(identifier: str) -> int:
        """
        Get failed OTP attempt count.
        """
        key = f"otp_attempts:{identifier}"
        return cache.get(key, 0)

    @staticmethod
    def set_reset_token(identifier: str, token: str, timeout: int = 900) -> bool:
        """
        Store password reset token in Redis (15-minute TTL).
        """
        key = f"reset_token:{identifier}"
        return cache.set(key, token, timeout=timeout)

    @staticmethod
    def get_reset_token(identifier: str) -> str | None:
        """
        Retrieve password reset token.
        """
        key = f"reset_token:{identifier}"
        return cache.get(key)

    @staticmethod
    def delete_reset_token(identifier: str) -> bool:
        """
        Delete reset token.
        """
        key = f"reset_token:{identifier}"
        return cache.delete(key)
