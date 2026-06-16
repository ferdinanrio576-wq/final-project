from .models import Coupon
from django.utils import timezone
from typing import Tuple

class CouponService:
    @staticmethod
    def validate_coupon(code: str, user, subtotal: float) -> Tuple[bool, float, str]:
        if not code:
            return False, 0.0, "Kode voucher kosong."
            
        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return False, 0.0, "Voucher tidak ditemukan."

        if not coupon.is_active:
            return False, 0.0, "Voucher sudah tidak aktif."

        if coupon.expiry_date and coupon.expiry_date < timezone.now().date():
            return False, 0.0, "Voucher telah kadaluwarsa."

        if coupon.active_limit and coupon.used_count >= coupon.active_limit:
            return False, 0.0, "Kuota penggunaan voucher telah habis."

        if subtotal < coupon.min_spend:
            return False, 0.0, f"Minimum belanja untuk menggunakan voucher ini adalah Rp {coupon.min_spend:,.0f}."

        # Calculate discount
        discount_amount = float(subtotal) * (coupon.discount_percentage / 100)
        
        # Apply cap if set
        if coupon.max_discount_amount and discount_amount > float(coupon.max_discount_amount):
            discount_amount = float(coupon.max_discount_amount)

        return True, discount_amount, "Voucher berhasil digunakan."
