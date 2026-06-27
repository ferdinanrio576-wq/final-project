import datetime
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="Voucher code, e.g. ELEKTRO2026")
    discount_percentage = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Maksimal nominal diskon")
    min_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Minimum belanja")
    expiry_date = models.DateField()
    active_limit = models.PositiveIntegerField(blank=True, null=True, help_text="Maksimal total penggunaan voucher")
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self, user, subtotal) -> bool:
        if not self.is_active:
            return False
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False
        if self.active_limit and self.used_count >= self.active_limit:
            return False
        if subtotal < self.min_spend:
            return False
        return True

    def __str__(self):
        return f"{self.code} - {self.discount_percentage}%"
