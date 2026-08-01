import re

from django.core.exceptions import ValidationError

GST_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
PAN_REGEX = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP", "AUD", "CAD", "JPY", "SGD"}


def validate_gst_number(value: str):
    if value and not re.match(GST_REGEX, value.upper()):
        raise ValidationError(
            "Invalid GST Number format. Must be a valid 15-character Indian GSTIN."
        )


def validate_pan_number(value: str):
    if value and not re.match(PAN_REGEX, value.upper()):
        raise ValidationError(
            "Invalid PAN Number format. Must be a valid 10-character Indian PAN."
        )


def validate_currency(value: str):
    if value and value.upper() not in SUPPORTED_CURRENCIES:
        raise ValidationError(
            f"Unsupported currency '{value}'. Supported currencies: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
        )
