import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("payment_gateway")


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_verification_email_task(self, email: str, otp: str):
    """
    Celery task to send email verification OTP.
    """
    try:
        subject = "Verify Your Payment Gateway Account"
        message = (
            f"Welcome to Payment Gateway Platform!\n\n"
            f"Your account verification OTP code is: {otp}\n\n"
            f"This code will expire in 5 minutes. If you did not register, please ignore this email."
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER or "noreply@stripe-gateway.com",
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Verification email sent successfully to {email}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send verification email to {email}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_password_reset_email_task(self, email: str, reset_token: str):
    """
    Celery task to send password reset token email.
    """
    try:
        subject = "Password Reset Request - Payment Gateway Platform"
        message = (
            f"Hello,\n\n"
            f"We received a request to reset your password. Use the token below to reset your password:\n\n"
            f"Reset Token: {reset_token}\n\n"
            f"This token will expire in 15 minutes. If you did not request a password reset, please ignore this message."
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER or "noreply@stripe-gateway.com",
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent successfully to {email}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send password reset email to {email}: {exc}")
        raise self.retry(exc=exc)
