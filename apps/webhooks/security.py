import hashlib
import hmac
import time
from typing import Tuple


def generate_webhook_signature(
    payload_str: str, secret_key: str, timestamp: int = None
) -> Tuple[str, int]:
    """
    Generates HMAC SHA-256 signature for Webhook payload with timestamp binding.
    Returns (signature_header, timestamp).
    """
    if timestamp is None:
        timestamp = int(time.time())

    signed_payload = f"{timestamp}.{payload_str}".encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()

    header_val = f"t={timestamp},v1={signature}"
    return header_val, timestamp


def verify_webhook_signature(
    payload_str: str,
    signature_header: str,
    secret_key: str,
    tolerance_seconds: int = 300,
) -> bool:
    """
    Verifies incoming Webhook HMAC signature header and enforces Replay Protection.
    """
    if not signature_header or not secret_key:
        return False

    parts = dict(pair.split("=") for pair in signature_header.split(",") if "=" in pair)
    timestamp_str = parts.get("t")
    received_sig = parts.get("v1")

    if not timestamp_str or not received_sig:
        return False

    try:
        ts = int(timestamp_str)
    except ValueError:
        return False

    # Replay Protection: Reject payloads older than tolerance window (e.g. 5 minutes)
    now = int(time.time())
    if abs(now - ts) > tolerance_seconds:
        return False

    expected_header, _ = generate_webhook_signature(
        payload_str, secret_key, timestamp=ts
    )
    expected_sig = dict(
        pair.split("=") for pair in expected_header.split(",") if "=" in pair
    ).get("v1")

    return hmac.compare_digest(received_sig, expected_sig)
