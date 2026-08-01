from unittest.mock import patch

import pytest
from accounts.models import User, UserRole
from accounts.permissions import (
    IsAdminPermission,
    IsCustomerPermission,
    IsMerchantPermission,
)
from accounts.repositories.user_repository import UserRepository
from accounts.services.auth_service import AuthService
from common.services.redis_service import RedisService
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestUserRepository:
    def test_create_user(self):
        user = UserRepository.create_user(
            email="testuser@example.com",
            password="StrongPassword123!",
            role=UserRole.CUSTOMER,
            first_name="John",
            last_name="Doe",
        )
        assert user.id is not None
        assert user.email == "testuser@example.com"
        assert user.role == UserRole.CUSTOMER
        assert user.check_password("StrongPassword123!") is True

    def test_get_by_email(self):
        user = UserRepository.create_user(
            email="search@example.com", password="Password123!"
        )
        found = UserRepository.get_by_email("SEARCH@example.com")
        assert found is not None
        assert found.id == user.id

    def test_set_email_verified(self):
        user = UserRepository.create_user(
            email="unverified@example.com", password="Password123!"
        )
        assert user.is_email_verified is False
        UserRepository.set_email_verified(user, True)
        user.refresh_from_db()
        assert user.is_email_verified is True


@pytest.mark.django_db
class TestAuthService:
    @patch("accounts.tasks.send_verification_email_task.delay")
    def test_register_user_success(self, mock_email_task):
        data = {
            "email": "newregister@example.com",
            "password": "Password123!",
            "role": UserRole.MERCHANT,
            "first_name": "Merchant",
            "last_name": "User",
        }
        user = AuthService.register_user(data)
        assert user.email == "newregister@example.com"
        assert user.role == UserRole.MERCHANT
        mock_email_task.assert_called_once()

    def test_login_user_success(self):
        user = UserRepository.create_user(
            email="login@example.com", password="Password123!"
        )
        user_obj, tokens = AuthService.login_user("login@example.com", "Password123!")
        assert user_obj.id == user.id
        assert "access" in tokens
        assert "refresh" in tokens

    def test_verify_email_otp(self):
        email = "otpverify@example.com"
        user = UserRepository.create_user(email=email, password="Password123!")
        RedisService.set_otp(email, "123456", timeout=300)

        res = AuthService.verify_email_otp(email, "123456")
        assert res is True
        user.refresh_from_db()
        assert user.is_email_verified is True

    def test_reset_password_flow(self):
        email = "resetflow@example.com"
        user = UserRepository.create_user(email=email, password="OldPassword123!")
        RedisService.set_reset_token(email, "valid-token-123", timeout=300)

        res = AuthService.reset_password(email, "valid-token-123", "NewPassword123!")
        assert res is True
        user.refresh_from_db()
        assert user.check_password("NewPassword123!") is True


@pytest.mark.django_db
class TestAccountsAPIEndpoints:
    @patch("accounts.tasks.send_verification_email_task.delay")
    def test_register_api_success(self, mock_email_task, api_client):
        url = reverse("accounts:register")
        payload = {
            "email": "api_reg@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "role": "CUSTOMER",
            "first_name": "Alice",
            "last_name": "Smith",
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "api_reg@example.com"

    def test_register_api_password_mismatch(self, api_client):
        url = reverse("accounts:register")
        payload = {
            "email": "mismatch@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
            "role": "CUSTOMER",
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_api_success(self, api_client):
        UserRepository.create_user(
            email="apilogin@example.com", password="Password123!"
        )
        url = reverse("accounts:login")
        payload = {"email": "apilogin@example.com", "password": "Password123!"}
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tokens" in data["data"]
        assert "access" in data["data"]["tokens"]

    def test_logout_api_success(self, api_client):
        UserRepository.create_user(
            email="apilogout@example.com", password="Password123!"
        )
        _, tokens = AuthService.login_user("apilogout@example.com", "Password123!")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        url = reverse("accounts:logout")
        payload = {"refresh": tokens["refresh"]}
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

    def test_user_profile_get_and_patch(self, api_client):
        UserRepository.create_user(
            email="profile@example.com",
            password="Password123!",
            first_name="OldName",
        )
        _, tokens = AuthService.login_user("profile@example.com", "Password123!")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        url = reverse("accounts:user_profile")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["first_name"] == "OldName"

        patch_res = api_client.patch(url, {"first_name": "NewName"}, format="json")
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.json()["data"]["first_name"] == "NewName"


@pytest.mark.django_db
class TestRolePermissions:
    def test_role_permission_classes(self):
        admin = User(role=UserRole.ADMIN)
        merchant = User(role=UserRole.MERCHANT)
        customer = User(role=UserRole.CUSTOMER)

        class MockRequest:
            def __init__(self, u):
                self.user = u

        assert IsAdminPermission().has_permission(MockRequest(admin), None) is True
        assert IsAdminPermission().has_permission(MockRequest(customer), None) is False

        assert (
            IsMerchantPermission().has_permission(MockRequest(merchant), None) is True
        )
        assert IsMerchantPermission().has_permission(MockRequest(admin), None) is False

        assert (
            IsCustomerPermission().has_permission(MockRequest(customer), None) is True
        )
        assert (
            IsCustomerPermission().has_permission(MockRequest(merchant), None) is False
        )
