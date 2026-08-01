from accounts.views import (
    ForgotPasswordView,
    LoginView,
    LogoutView,
    RegisterView,
    ResendOTPView,
    ResetPasswordView,
    TokenRefreshView,
    UserProfileView,
    VerifyEmailOTPView,
)
from django.urls import path

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("email/verify/", VerifyEmailOTPView.as_view(), name="verify_email"),
    path("email/resend-otp/", ResendOTPView.as_view(), name="resend_otp"),
    path("password/forgot/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("password/reset/", ResetPasswordView.as_view(), name="reset_password"),
    path("me/", UserProfileView.as_view(), name="user_profile"),
]
