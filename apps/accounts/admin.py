from accounts.models import User
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "role",
        "first_name",
        "last_name",
        "is_email_verified",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_email_verified", "is_staff", "is_active", "is_deleted")
    search_fields = ("email", "first_name", "last_name", "phone_number")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone_number")}),
        ("Role & Verification", {"fields": ("role", "is_email_verified")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("Soft Delete", {"fields": ("is_deleted", "deleted_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_email_verified",
                ),
            },
        ),
    )
