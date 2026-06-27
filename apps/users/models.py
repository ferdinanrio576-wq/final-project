import random
import string
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        CUSTOMER = 'CUSTOMER', 'Customer'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_banned = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    # Use email as primary login field instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_admin_user(self):
        return self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN]


class Profile(models.Model):
    GENDER_CHOICES = (
        ('M', 'Laki-laki'),
        ('F', 'Perempuan'),
        ('O', 'Lainnya'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, default='Rumah', help_text="Contoh: Rumah, Kantor")
    recipient_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    street_address = models.TextField()
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    place_id = models.CharField(max_length=255, blank=True, null=True, help_text="Google Place ID untuk verifikasi alamat")
    latitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other addresses of this user to not default
            Address.objects.filter(user=self.user).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.label} - {self.recipient_name} ({self.city})"


class EmailOTP(models.Model):
    """Model untuk menyimpan OTP verifikasi email - berlaku 10 menit."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_otps')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Cek apakah OTP masih valid (belum expired dan belum digunakan)."""
        return not self.is_used and timezone.now() < self.expires_at

    @classmethod
    def generate_otp(cls):
        """Generate kode OTP 6 digit angka."""
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def mask_email(email: str) -> str:
        """Masking email untuk tampilan privasi: ra***@gmail.com"""
        parts = email.split('@')
        if len(parts) != 2:
            return email
        local = parts[0]
        domain = parts[1]
        if len(local) <= 2:
            masked_local = local[0] + '***'
        else:
            masked_local = local[:2] + '***'
        return f"{masked_local}@{domain}"

    def __str__(self):
        return f"OTP for {self.user.email} ({'valid' if self.is_valid() else 'expired/used'})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'
