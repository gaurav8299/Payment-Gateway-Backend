import hashlib
import hmac
import secrets
import string


def generate_unique_id(prefix: str, length: int = 24) -> str:
    """
    Generate a cryptographically secure random unique ID with a specified prefix.
    Example: generate_unique_id('ord') -> 'ord_9a8f7c6e5d4c3b2a10fe'
    """
    alphabet = string.ascii_lowercase + string.digits
    random_str = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}_{random_str}"


def hash_secret(raw_secret: str) -> str:
    """
    Compute SHA-256 hash of a string (e.g. API keys).
    """
    return hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()


def generate_hmac_signature(payload: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload verification.
    """
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
