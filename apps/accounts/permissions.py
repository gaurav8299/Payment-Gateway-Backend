from accounts.models import UserRole
from rest_framework.permissions import BasePermission


class IsAdminPermission(BasePermission):
    """
    Allows access only to authenticated users with ADMIN role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.ADMIN
        )


class IsMerchantPermission(BasePermission):
    """
    Allows access only to authenticated users with MERCHANT role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.MERCHANT
        )


class IsCustomerPermission(BasePermission):
    """
    Allows access only to authenticated users with CUSTOMER role.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.CUSTOMER
        )


class IsOwnerOrAdminPermission(BasePermission):
    """
    Object-level permission allowing access to object owners or Admins.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            return True
        owner = getattr(obj, "user", obj)
        return owner == request.user
