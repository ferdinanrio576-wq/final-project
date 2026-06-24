import os
import sys
import django
from django.core.files import File

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'electro_shop.settings')
django.setup()

from products.models import Category, Brand, Product, ProductSpecification, ProductImage

def seed_laptops():
    cat_laptop, _ = Category.objects.get_or_create(name='Laptop', slug='laptop')
    
    brand_lenovo, _ = Brand.objects.get_or_create(name='Lenovo', slug='lenovo')
    brand_acer, _ = Brand.objects.get_or_create(name='Acer', slug='acer')
    brand_msi, _ = Brand.objects.get_or_create(name='MSI', slug='msi')

    # 1. Lenovo Legion Pro
    if not Product.objects.filter(sku='LEGION-PRO5').exists():
        prod1 = Product.objects.create(
            name='Lenovo Legion Pro 5',
            sku='LEGION-PRO5',
            description='Laptop gaming tangguh dengan prosesor Intel Core i7 Generasi ke-13 dan grafis RTX 4070.',
            price=28999000.00,
            stock=10,
            weight_grams=2500,
            category=cat_laptop,
            brand=brand_lenovo,
            is_active=True,
            is_featured=True
        )
        ProductSpecification.objects.create(product=prod1, name='Processor', value='Intel Core i7-13700HX')
        ProductSpecification.objects.create(product=prod1, name='RAM', value='16GB DDR5 4800MHz')
        ProductSpecification.objects.create(product=prod1, name='Storage', value='1TB SSD NVMe')
        ProductSpecification.objects.create(product=prod1, name='VGA', value='RTX 4070 8GB')
        
        # Add Image
        img_path = r'C:\Users\MSI\.gemini\antigravity\brain\b73475c9-3c86-45fd-aba9-78f80ed03a49\lenovo_legion_1782211894129.png'
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                ProductImage.objects.create(product=prod1, image=File(f, name='lenovo_legion.png'), is_primary=True)
        print("Produk Lenovo Legion Pro 5 berhasil ditambahkan.")

    # 2. Acer Predator Helios
    if not Product.objects.filter(sku='HELIOS-NEO').exists():
        prod2 = Product.objects.create(
            name='Acer Predator Helios Neo 16',
            sku='HELIOS-NEO',
            description='Nikmati performa gaming maksimal dengan Acer Predator Helios Neo 16 yang dibekali sistem pendingin canggih.',
            price=25499000.00,
            discount_price=24999000.00,
            stock=8,
            weight_grams=2600,
            category=cat_laptop,
            brand=brand_acer,
            is_active=True,
            is_featured=True
        )
        ProductSpecification.objects.create(product=prod2, name='Processor', value='Intel Core i7-13700HX')
        ProductSpecification.objects.create(product=prod2, name='RAM', value='16GB DDR5 4800MHz')
        ProductSpecification.objects.create(product=prod2, name='Storage', value='1TB SSD NVMe')
        ProductSpecification.objects.create(product=prod2, name='VGA', value='RTX 4060 8GB')
        
        # Add Image
        img_path = r'C:\Users\MSI\.gemini\antigravity\brain\b73475c9-3c86-45fd-aba9-78f80ed03a49\acer_predator_1782211930408.png'
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                ProductImage.objects.create(product=prod2, image=File(f, name='acer_predator.png'), is_primary=True)
        print("Produk Acer Predator Helios Neo 16 berhasil ditambahkan.")

    # 3. MSI Katana 15
    if not Product.objects.filter(sku='KATANA-15').exists():
        prod3 = Product.objects.create(
            name='MSI Katana 15 B13V',
            sku='KATANA-15',
            description='Laptop gaming andal dan stylish dengan keyboard RGB dan tenaga Intel i7 Gen 13.',
            price=21999000.00,
            stock=15,
            weight_grams=2250,
            category=cat_laptop,
            brand=brand_msi,
            is_active=True,
            is_featured=False
        )
        ProductSpecification.objects.create(product=prod3, name='Processor', value='Intel Core i7-13620H')
        ProductSpecification.objects.create(product=prod3, name='RAM', value='16GB DDR5')
        ProductSpecification.objects.create(product=prod3, name='Storage', value='512GB SSD NVMe')
        ProductSpecification.objects.create(product=prod3, name='VGA', value='RTX 4050 6GB')
        
        # Add Image
        img_path = r'C:\Users\MSI\.gemini\antigravity\brain\b73475c9-3c86-45fd-aba9-78f80ed03a49\msi_katana_1782211963700.png'
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                ProductImage.objects.create(product=prod3, image=File(f, name='msi_katana.png'), is_primary=True)
        print("Produk MSI Katana 15 B13V berhasil ditambahkan.")

if __name__ == '__main__':
    seed_laptops()
