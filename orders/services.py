import time
import math
from decimal import Decimal

from .repositories import CartRepository, OrderRepository, WishlistRepository
from .models import Cart, CartItem, Order, OrderItem, Shipment
from products.models import Product
from users.models import Address
from coupons.models import Coupon
from django.db import OperationalError, transaction

# Titik Penjual (Purwokerto)
PURWOKERTO_LAT = -7.424494
PURWOKERTO_LNG = 109.230154

# ─── Tarif Pengiriman Per Kurir & Paket ────────────────────────────────────────
# Format: { 'KURIR': { 'PAKET': {'label': ..., 'base_rate_per_kg': ..., 'rate_per_km_per_kg': ..., 'estimate': ...} } }
SHIPPING_PACKAGES = {
    'JNE': {
        'REG': {'label': 'REG (Reguler)', 'rate_per_kg': 9000, 'base_rate_per_kg': 9000, 'rate_per_km_per_kg': 200, 'estimate': '2-5 hari kerja'},
        'YES': {'label': 'YES (Yakin Esok Sampai)', 'rate_per_kg': 22000, 'base_rate_per_kg': 22000, 'rate_per_km_per_kg': 400, 'estimate': '1 hari kerja'},
        'OKE': {'label': 'OKE (Ongkos Kirim Ekonomis)', 'rate_per_kg': 7000, 'base_rate_per_kg': 7000, 'rate_per_km_per_kg': 150, 'estimate': '5-7 hari kerja'},
    },
    'TIKI': {
        'REG': {'label': 'REG (Regular)', 'rate_per_kg': 10000, 'base_rate_per_kg': 10000, 'rate_per_km_per_kg': 220, 'estimate': '2-4 hari kerja'},
        'ONS': {'label': 'ONS (Over Night Service)', 'rate_per_kg': 25000, 'base_rate_per_kg': 25000, 'rate_per_km_per_kg': 450, 'estimate': '1 hari kerja'},
        'ECO': {'label': 'ECO (Economy)', 'rate_per_kg': 8000, 'base_rate_per_kg': 8000, 'rate_per_km_per_kg': 160, 'estimate': '5-8 hari kerja'},
    },
    'POS': {
        'BIASA': {'label': 'Paket Biasa', 'rate_per_kg': 8000, 'base_rate_per_kg': 8000, 'rate_per_km_per_kg': 140, 'estimate': '3-7 hari kerja'},
        'KILAT': {'label': 'Paket Kilat', 'rate_per_kg': 18000, 'base_rate_per_kg': 18000, 'rate_per_km_per_kg': 350, 'estimate': '1-2 hari kerja'},
    },
}


def calculate_shipping_cost(courier: str, service: str, total_weight_grams: int, destination_province: str = None, latitude=None, longitude=None) -> int:
    """Hitung ongkir berdasarkan kurir, paket, berat total (dalam gram), dan jarak dari Purwokerto."""
    courier_data = SHIPPING_PACKAGES.get(courier.upper(), {})
    service_data = courier_data.get(service.upper(), None)

    if not service_data:
        # Fallback: base rate default Rp 9.000/kg, rate per km Rp 200/kg
        base_rate = 9000
        rate_per_km = 200
    else:
        base_rate = service_data.get('base_rate_per_kg', service_data.get('rate_per_kg', 9000))
        rate_per_km = service_data.get('rate_per_km_per_kg', 200)

    # Hitung Jarak (km) dari Purwokerto menggunakan formula Haversine
    distance_km = None
    if latitude is not None and longitude is not None:
        try:
            lat1 = float(PURWOKERTO_LAT)
            lon1 = float(PURWOKERTO_LNG)
            lat2 = float(latitude)
            lon2 = float(longitude)
            
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
            distance_km = 6371.0 * c
        except (ValueError, TypeError):
            pass

    # Fallback jarak berdasarkan nama provinsi jika koordinat kosong/gagal dihitung
    if distance_km is None:
        if destination_province:
            norm = destination_province.strip().lower()
            if 'tengah' in norm or 'yogyakarta' in norm or 'diy' in norm:
                distance_km = 100.0  # Jawa Tengah / DIY
            elif 'barat' in norm or 'banten' in norm:
                distance_km = 250.0  # Jawa Barat / Banten
            elif 'jakarta' in norm or 'dki' in norm:
                distance_km = 350.0  # DKI Jakarta
            elif 'timur' in norm:
                distance_km = 400.0  # Jawa Timur
            else:
                distance_km = 1200.0 # Luar Jawa
        else:
            distance_km = 10.0  # Jarak lokal default

    # Rumus Ongkir: (Base Rate + Jarak * Rate per km) * Berat dalam kg (min 1 kg)
    weight_kg = max(1.0, total_weight_grams / 1000.0)
    cost_per_kg = base_rate + (rate_per_km * distance_km)
    total_cost = round(cost_per_kg * weight_kg)
    
    # Bulatkan ke kelipatan Rp 500 terdekat
    total_cost = round(total_cost / 500.0) * 500
    
    return int(max(5000, total_cost)) # Minimum ongkir Rp 5.000


class CartService:
    def __init__(self):
        self.cart_repo = CartRepository()

    def get_cart(self, user=None, session_key: str = None) -> Cart:
        if user and user.is_authenticated:
            cart, _ = self.cart_repo.get_user_cart(user)
            if session_key:
                session_cart = Cart.objects.filter(session_key=session_key).first()
                if session_cart and session_cart != cart:
                    self.cart_repo.merge_carts(session_cart, cart)
            return cart
        elif session_key:
            cart, _ = self.cart_repo.get_session_cart(session_key)
            return cart
        raise ValueError("User atau Session Key harus disediakan untuk mendapatkan Cart.")

    def add_item(self, cart: Cart, product_id: int, quantity: int = 1) -> CartItem:
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise ValueError("Produk tidak ditemukan atau tidak aktif.")

        if product.stock < quantity:
            raise ValueError("Stok produk tidak mencukupi.")

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            if product.stock < (item.quantity + quantity):
                raise ValueError("Stok produk tidak mencukupi untuk jumlah ini.")
            item.quantity += quantity
            item.save()
        return item

    def update_quantity(self, cart: Cart, product_id: int, quantity: int) -> CartItem:
        try:
            item = CartItem.objects.get(cart=cart, product_id=product_id)
        except CartItem.DoesNotExist:
            raise ValueError("Item keranjang tidak ditemukan.")

        if item.product.stock < quantity:
            raise ValueError("Stok produk tidak mencukupi.")

        item.quantity = quantity
        item.save()
        return item

    def remove_item(self, cart: Cart, product_id: int):
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()


def retry_on_database_lock(func):
    def wrapper(*args, **kwargs):
        attempts = 5
        delay = 1
        for attempt in range(attempts):
            try:
                return func(*args, **kwargs)
            except OperationalError as exc:
                message = str(exc).lower()
                if 'database is locked' not in message or attempt == attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 2
    return wrapper


class OrderService:
    def __init__(self):
        self.order_repo = OrderRepository()

    @retry_on_database_lock
    @transaction.atomic
    def checkout(
        self, user, cart: Cart, address: Address, courier: str,
        coupon_code: str = None, shipping_service: str = None, destination_province: str = None
    ) -> Order:
        if cart.items.count() == 0:
            raise ValueError("Keranjang belanja kosong.")

        # Validasi stok sebelum lanjut
        for item in cart.items.all():
            if item.product.stock < item.quantity:
                raise ValueError(f"Stok produk '{item.product.name}' tidak mencukupi.")

        subtotal = cart.subtotal

        # Hitung total berat
        total_weight = sum(item.product.weight_grams * item.quantity for item in cart.items.all())

        # Tentukan paket layanan (default REG jika tidak dipilih)
        courier_upper = courier.upper() if courier else 'JNE'
        service_upper = (shipping_service or 'REG').upper()

        # Validasi service ada untuk kurir yang dipilih
        courier_packages = SHIPPING_PACKAGES.get(courier_upper, {})
        if service_upper not in courier_packages:
            # Ambil paket pertama yang tersedia
            service_upper = list(courier_packages.keys())[0] if courier_packages else 'REG'

        shipping_cost = calculate_shipping_cost(
            courier=courier_upper,
            service=service_upper,
            total_weight_grams=total_weight,
            destination_province=destination_province,
            latitude=address.latitude,
            longitude=address.longitude
        )

        # Pajak (PPN 11%)
        tax_amount = round(subtotal * Decimal('0.11'))

        # Diskon kupon
        discount_amount = 0
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
                if coupon.is_valid(user, subtotal):
                    discount_amount = round(subtotal * Decimal(coupon.discount_percentage) / Decimal('100'))
                    if coupon.max_discount_amount and discount_amount > coupon.max_discount_amount:
                        discount_amount = coupon.max_discount_amount
                    coupon.used_count += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass

        final_amount = (subtotal + Decimal(shipping_cost) + Decimal(tax_amount)) - Decimal(discount_amount)

        import random
        max_attempts = 100
        unique_code = random.randint(100, 999)
        attempts = 0
        while Order.objects.filter(
            status__in=[Order.Status.PENDING, Order.Status.AWAITING_VERIFICATION],
            unique_code=unique_code
        ).exists() and attempts < max_attempts:
            unique_code = random.randint(100, 999)
            attempts += 1

        payment_amount = final_amount + Decimal(unique_code)

        # Buat Order
        order = self.order_repo.create_order(
            user=user,
            address=address,
            total_amount=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            unique_code=unique_code,
            payment_amount=payment_amount,
            coupon=coupon
        )

        # Simpan shipping_service ke Order
        order.shipping_service = service_upper
        order.save()

        # Buat Order Items dan kurangi stok
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.final_price,
                quantity=item.quantity
            )
            item.product.stock -= item.quantity
            item.product.save()

        # Buat Shipment record dengan service
        Shipment.objects.create(
            order=order,
            courier=courier_upper,
            service=service_upper,
            status=Shipment.Status.PENDING
        )

        # Bersihkan Keranjang
        cart.items.all().delete()

        # Notifikasi in-app
        from notifications.services import NotificationService
        notif_service = NotificationService()
        notif_service.create_notification(
            user=user,
            title="Pesanan Berhasil Dibuat",
            message=f"Pesanan Anda dengan nomor {order.order_number} berhasil dibuat. Silakan selesaikan pembayaran Anda.",
            notif_type="ORDER"
        )

        return order


class WishlistService:
    def __init__(self):
        self.wishlist_repo = WishlistRepository()

    def toggle_wishlist(self, user, product_id: int) -> bool:
        wishlist, _ = self.wishlist_repo.get_or_create_wishlist(user)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValueError("Produk tidak ditemukan.")

        if product in wishlist.products.all():
            wishlist.products.remove(product)
            return False
        else:
            wishlist.products.add(product)
            return True
