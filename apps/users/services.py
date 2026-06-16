from .repositories import UserRepository, AddressRepository
from .models import User, Profile, Address
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

class UserService:
    def __init__(self):
        self.user_repo = UserRepository()

    def register_customer(self, email: str, username: str, password: str) -> User:
        return self.user_repo.create_user(
            email=email, 
            username=username, 
            password=password, 
            role=User.Role.CUSTOMER
        )

    def update_profile(
        self, user: User, phone_number: str = None, avatar = None, 
        birth_date = None, gender: str = None
    ) -> Profile:
        profile, created = Profile.objects.get_or_create(user=user)
        if phone_number is not None:
            profile.phone_number = phone_number
        if avatar is not None:
            profile.avatar = avatar
        if birth_date is not None:
            profile.birth_date = birth_date
        if gender is not None:
            profile.gender = gender
        profile.save()
        return profile

    def send_verification_email(self, user: User, request) -> None:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        verify_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        )
        subject = 'Verifikasi Email Anda di ElectroShop'
        context = {
            'user': user,
            'verify_url': verify_url,
        }
        message = render_to_string('auth/email_verification_email.txt', context)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

    def verify_email(self, uidb64: str, token: str) -> bool:
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return False

        if default_token_generator.check_token(user, token):
            user.email_verified = True
            user.save()
            return True
        return False


class AddressService:
    def __init__(self):
        self.address_repo = AddressRepository()

    def add_address(
        self, user: User, label: str, recipient_name: str, phone_number: str,
        street_address: str, city: str, province: str, postal_code: str,
        is_default: bool = False
    ) -> Address:
        return self.address_repo.create_address(
            user=user, label=label, recipient_name=recipient_name, phone_number=phone_number,
            street_address=street_address, city=city, province=province, postal_code=postal_code,
            is_default=is_default
        )

    def set_default(self, address_id: int, user: User) -> bool:
        address = self.address_repo.get_by_id(address_id, user)
        if address:
            address.is_default = True
            address.save()
            return True
        return False

    def delete_address(self, address_id: int, user: User) -> bool:
        address = self.address_repo.get_by_id(address_id, user)
        if address:
            # If we delete a default address, assign default to another if exists
            was_default = address.is_default
            address.delete()
            if was_default:
                remaining = Address.objects.filter(user=user).first()
                if remaining:
                    remaining.is_default = True
                    remaining.save()
            return True
        return False
