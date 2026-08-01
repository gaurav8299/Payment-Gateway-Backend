from decimal import Decimal
from typing import Any
from uuid import UUID

SENSITIVE_KEYS = {
    "password",
    "confirm_password",
    "token",
    "access",
    "refresh",
    "secret",
    "secret_key",
    "hashed_secret_key",
    "otp",
    "card_number",
    "cvv",
    "cvc",
    "api_key",
    "x-api-key",
    "authorization",
}


def sanitize_payload(data: Any) -> Any:
    """
    Recursively inspects dicts and lists to mask sensitive fields (passwords, JWT tokens, secrets, OTPs)
    and casts non-JSON-serializable objects (UUIDs, Decimals) to string.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_payload(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    elif isinstance(data, (UUID, Decimal)):
        return str(data)
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        return str(data)
