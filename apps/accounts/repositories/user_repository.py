from typing import Optional
from uuid import UUID

from accounts.models import User, UserRole


class UserRepository:
    """
    Repository class handling database access for User entities.
    """

    @staticmethod
    def create_user(
        email: str,
        password: str,
        role: str = UserRole.CUSTOMER,
        first_name: str = "",
        last_name: str = "",
        phone_number: Optional[str] = None,
    ) -> User:
        user = User.objects.create_user(
            email=email,
            password=password,
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        return user

    @staticmethod
    def get_by_id(user_id: UUID | str) -> Optional[User]:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def exists_by_email(email: str) -> bool:
        return User.objects.filter(email__iexact=email).exists()

    @staticmethod
    def update_user(user: User, **kwargs) -> User:
        for attr, value in kwargs.items():
            if hasattr(user, attr) and value is not None:
                setattr(user, attr, value)
        user.save()
        return user

    @staticmethod
    def set_email_verified(user: User, is_verified: bool = True) -> User:
        user.is_email_verified = is_verified
        user.save(update_fields=["is_email_verified"])
        return user

    @staticmethod
    def set_password(user: User, raw_password: str) -> User:
        user.set_password(raw_password)
        user.save(update_fields=["password"])
        return user
