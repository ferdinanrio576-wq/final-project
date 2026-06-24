import os
import sys
import django
import datetime

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'electro_shop.settings')
django.setup()

from coupons.models import Coupon

def seed_coupons():
    print("Mulai proses seeding data kupon...")
    today = datetime.date.today()
    expiry = today + datetime.timedelta(days=90)

    coupons_data = [
        {
            'code': 'NEWUSER',
            'discount_percentage': 50,
            'max_discount_amount': 50000.00,
            'min_spend': 50000.00,
            'expiry_date': expiry,
            'active_limit': 100,
            'is_active': True
        },
        {
            'code': 'HEMATPROMO',
            'discount_percentage': 5,
            'max_discount_amount': 200000.00,
            'min_spend': 500000.00,
            'expiry_date': expiry,
            'active_limit': 200,
            'is_active': True
        },
        {
            'code': 'SUPERDEAL',
            'discount_percentage': 10,
            'max_discount_amount': 500000.00,
            'min_spend': 3000000.00,
            'expiry_date': expiry,
            'active_limit': 50,
            'is_active': True
        },
        {
            'code': 'MEGASALE',
            'discount_percentage': 15,
            'max_discount_amount': 1500000.00,
            'min_spend': 8000000.00,
            'expiry_date': expiry,
            'active_limit': 50,
            'is_active': True
        },
        {
            'code': 'LAPTOPBARU',
            'discount_percentage': 8,
            'max_discount_amount': 2500000.00,
            'min_spend': 15000000.00,
            'expiry_date': expiry,
            'active_limit': 30,
            'is_active': True
        }
    ]

    for item in coupons_data:
        coupon, created = Coupon.objects.update_or_create(
            code=item['code'],
            defaults=item
        )
        if created:
            print(f"Kupon baru berhasil dibuat: {coupon.code}")
        else:
            print(f"Kupon {coupon.code} berhasil diperbarui.")

    print("Seeding data kupon selesai!")

if __name__ == '__main__':
    seed_coupons()
