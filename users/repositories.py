from .models import User, Profile, Address
from typing import Optional, List

class UserRepository:
    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def create_user(email: str, username: str, password: str, role: str = User.Role.CUSTOMER) -> User:
        user = User.objects.create_user(
            email=email, 
            username=username, 
            password=password, 
            role=role
        )
        return user


class AddressRepository:
    @staticmethod
    def get_user_addresses(user: User) -> List[Address]:
        return list(Address.objects.filter(user=user).order_by('-is_default', '-created_at'))

    @staticmethod
    def get_by_id(address_id: int, user: User) -> Optional[Address]:
        try:
            return Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            return None

    @staticmethod
    def create_address(
        user: User, label: str, recipient_name: str, phone_number: str, 
        street_address: str, city: str, province: str, postal_code: str, 
        is_default: bool = False
    ) -> Address:
        return Address.objects.create(
            user=user,
            label=label,
            recipient_name=recipient_name,
            phone_number=phone_number,
            street_address=street_address,
            city=city,
            province=province,
            postal_code=postal_code,
            is_default=is_default
        )
