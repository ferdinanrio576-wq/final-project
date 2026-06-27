from .repositories import UserRepository, AddressRepository
from .models import User, Profile, Address, EmailOTP
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone


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
        self, user: User, phone_number: str = None, avatar=None,
        birth_date=None, gender: str = None
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

    # ─── OTP Email Verification ────────────────────────────────────────────────

    def send_otp_email(self, user: User) -> EmailOTP:
        """Generate OTP 6 digit, simpan ke DB, kirim ke email user."""
        # Nonaktifkan semua OTP lama yang belum digunakan
        EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)

        # Buat OTP baru
        otp_code = EmailOTP.generate_otp()
        otp = EmailOTP.objects.create(user=user, otp_code=otp_code)

        # Kirim email OTP
        subject = f'Kode Verifikasi ElectroShop: {otp_code}'
        masked_email = EmailOTP.mask_email(user.email)

        # Plain text fallback
        text_content = (
            f"Halo {user.username},\n\n"
            f"Kode verifikasi Anda: {otp_code}\n\n"
            f"Kode ini berlaku selama 10 menit.\n"
            f"Jika Anda tidak mendaftar di ElectroShop, abaikan email ini.\n\n"
            f"Tim ElectroShop"
        )

        # HTML email
        html_content = render_to_string('auth/email_otp.html', {
            'user': user,
            'otp_code': otp_code,
            'masked_email': masked_email,
        })

        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send(fail_silently=False)

        return otp

    def verify_otp(self, user: User, otp_code: str) -> tuple[bool, str]:
        """
        Verifikasi OTP user.
        Returns: (success: bool, message: str)
        """
        # Ambil OTP terbaru yang belum digunakan
        otp = EmailOTP.objects.filter(
            user=user,
            is_used=False
        ).order_by('-created_at').first()

        if not otp:
            return False, "Kode OTP tidak ditemukan. Silakan minta kirim ulang."

        if timezone.now() > otp.expires_at:
            return False, "Kode OTP sudah kadaluarsa. Silakan minta kirim ulang."

        if otp.otp_code != otp_code.strip():
            return False, "Kode OTP salah. Periksa kembali email Anda."

        # OTP valid — tandai sebagai digunakan
        otp.is_used = True
        otp.save()

        # Verifikasi akun user
        user.email_verified = True
        user.save()

        return True, "Email berhasil diverifikasi!"

    # ─── Link-based Verification (Backward Compat) ────────────────────────────

    def send_verification_email(self, user: User, request) -> None:
        """Verifikasi via link token (metode lama - dipertahankan untuk compat)."""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        verify_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        )
        subject = 'Verifikasi Email Anda di ElectroShop'
        context = {'user': user, 'verify_url': verify_url}
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
            was_default = address.is_default
            address.delete()
            if was_default:
                remaining = Address.objects.filter(user=user).first()
                if remaining:
                    remaining.is_default = True
                    remaining.save()
            return True
        return False
