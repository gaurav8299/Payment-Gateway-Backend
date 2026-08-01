import uuid

from common.models import SoftDeleteModel, TimeStampedModel
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    MERCHANT = "MERCHANT", "Merchant"
    CUSTOMER = "CUSTOMER", "Customer"


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier for authentication.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, TimeStampedModel, SoftDeleteModel):
    """
    Production User Entity for Payment Gateway Backend.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        db_index=True,
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False, db_index=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} [{self.role}]"
