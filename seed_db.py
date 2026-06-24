import os
import sys
import django

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'electro_shop.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Profile, Address
from products.models import Category, Brand, Product, ProductSpecification
from coupons.models import Coupon
import datetime

User = get_user_model()

def seed_data():
    print("Mulai proses seeding data...")

    # 1. Buat Akun Pengguna
    # Super Admin
    super_admin_email = 'superadmin@electroshop.com'
    if not User.objects.filter(email=super_admin_email).exists():
        super_admin = User.objects.create_superuser(
            email=super_admin_email,
            username='superadmin',
            password='superadmin123',
            role=User.Role.SUPER_ADMIN,
            email_verified=True
        )
        print(f"Super Admin sukses dibuat: {super_admin_email} / superadmin123")
    else:
        print("Super Admin sudah ada.")

    # Admin
    admin_email = 'admin@electroshop.com'
    if not User.objects.filter(email=admin_email).exists():
        admin = User.objects.create_user(
            email=admin_email,
            username='admin',
            password='admin123',
            role=User.Role.ADMIN,
            is_staff=True,
            email_verified=True
        )
        print(f"Admin sukses dibuat: {admin_email} / admin123")
    else:
        print("Admin sudah ada.")

    # Customer
    customer_email = 'customer@electroshop.com'
    if not User.objects.filter(email=customer_email).exists():
        customer = User.objects.create_user(
            email=customer_email,
            username='customer',
            password='customer123',
            role=User.Role.CUSTOMER,
            email_verified=True
        )
        
        # Buat alamat default untuk Customer
        Address.objects.create(
            user=customer,
            label='Rumah',
            recipient_name='Budi Santoso',
            phone_number='081234567890',
            street_address='Jl. Mangga Dua No. 15, RT 05 / RW 02',
            city='Jakarta Pusat',
            province='DKI Jakarta',
            postal_code='10730',
            is_default=True
        )
        print(f"Customer sukses dibuat: {customer_email} / customer123 (lengkap dengan alamat utama)")
    else:
        print("Customer sudah ada.")

    # 2. Buat Brand
    brand_asus, _ = Brand.objects.get_or_create(name='ASUS', slug='asus', description='ASUS Global Tech')
    brand_samsung, _ = Brand.objects.get_or_create(name='Samsung', slug='samsung', description='Samsung Electronics Co.')
    brand_apple, _ = Brand.objects.get_or_create(name='Apple', slug='apple', description='Apple Inc. California')
    print("Brands sukses dibuat.")

    # 3. Buat Kategori
    cat_laptop, _ = Category.objects.get_or_create(name='Laptop', slug='laptop', description='Laptop Kerja, Gaming, & Ultraportable')
    cat_phone, _ = Category.objects.get_or_create(name='Smartphone', slug='smartphone', description='Smartphone & Phablet Android / iOS')
    cat_acc, _ = Category.objects.get_or_create(name='Aksesoris', slug='aksesoris', description='Mouse, Keyboard, Headset, & Aksesoris lainnya')
    print("Categories sukses dibuat.")

    # 4. Buat Produk
    # Laptop ASUS ROG
    if not Product.objects.filter(sku='ROG-G14').exists():
        prod1 = Product.objects.create(
            name='ASUS ROG Zephyrus G14',
            sku='ROG-G14',
            description='Laptop gaming 14 inci terbaik dengan AMD Ryzen 9 dan NVIDIA RTX 4060. Layar ROG Nebula Display OLED 120Hz.',
            price=24999000.00,
            discount_price=23499000.00,
            stock=12,
            weight_grams=1650,
            category=cat_laptop,
            brand=brand_asus,
            is_active=True,
            is_featured=True
        )
        ProductSpecification.objects.create(product=prod1, name='Processor', value='AMD Ryzen 9 8945HS')
        ProductSpecification.objects.create(product=prod1, name='RAM', value='16GB DDR5 5600MHz')
        ProductSpecification.objects.create(product=prod1, name='Storage', value='1TB NVMe PCIe Gen 4 SSD')
        ProductSpecification.objects.create(product=prod1, name='Graphics Card', value='NVIDIA GeForce RTX 4060 8GB GDDR6')
        print("Produk 1 (ASUS ROG) sukses dibuat.")

    # Samsung S24 Ultra
    if not Product.objects.filter(sku='S24-ULTRA').exists():
        prod2 = Product.objects.create(
            name='Samsung Galaxy S24 Ultra 5G',
            sku='S24-ULTRA',
            description='Smartphone flagship Samsung terbaru dengan Galaxy AI. Kamera utama 200MP, S-Pen terintegrasi, dan rangka Titanium.',
            price=21999000.00,
            stock=25,
            weight_grams=232,
            category=cat_phone,
            brand=brand_samsung,
            is_active=True,
            is_featured=True
        )
        ProductSpecification.objects.create(product=prod2, name='Layar', value='6.8 inci Dynamic AMOLED 2X, 120Hz')
        ProductSpecification.objects.create(product=prod2, name='Processor', value='Snapdragon 8 Gen 3 for Galaxy')
        ProductSpecification.objects.create(product=prod2, name='Kamera Utama', value='200MP + 50MP + 12MP + 10MP')
        ProductSpecification.objects.create(product=prod2, name='Baterai', value='5000mAh dengan 45W Fast Charging')
        print("Produk 2 (Samsung S24 Ultra) sukses dibuat.")

    # Apple iPhone 15 Pro
    if not Product.objects.filter(sku='IPHONE-15P').exists():
        prod3 = Product.objects.create(
            name='Apple iPhone 15 Pro Max',
            sku='IPHONE-15P',
            description='iPhone pertama dengan desain Titanium sekelas industri dirgantara, chip A17 Pro revolusioner, dan sistem kamera super kuat.',
            price=24999000.00,
            stock=8,
            weight_grams=221,
            category=cat_phone,
            brand=brand_apple,
            is_active=True,
            is_featured=False
        )
        ProductSpecification.objects.create(product=prod3, name='Layar', value='6.7 inci Super Retina XDR OLED ProMotion')
        ProductSpecification.objects.create(product=prod3, name='Processor', value='Apple A17 Pro (3nm)')
        ProductSpecification.objects.create(product=prod3, name='Kamera Utama', value='48MP + 12MP + 12MP zoom 5x')
        ProductSpecification.objects.create(product=prod3, name='Port Pengisian', value='USB Type-C 3.0')
        print("Produk 3 (iPhone 15 Pro Max) sukses dibuat.")

    # 5. Buat Voucher Coupon
    if not Coupon.objects.filter(code='ELEKTRO2026').exists():
        Coupon.objects.create(
            code='ELEKTRO2026',
            discount_percentage=10,
            max_discount_amount=1000000.00,
            min_spend=5000000.00,
            expiry_date=datetime.date.today() + datetime.timedelta(days=90),
            active_limit=100,
            is_active=True
        )
        print("Voucher ELEKTRO2026 sukses dibuat (Diskon 10% s.d Rp 1.000.000, Min. Belanja Rp 5.000.000)")

    print("Seeding database selesai dengan sukses!")

if __name__ == '__main__':
    seed_data()
