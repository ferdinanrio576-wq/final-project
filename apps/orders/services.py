import time
from decimal import Decimal

from .repositories import CartRepository, OrderRepository, WishlistRepository
from .models import Cart, CartItem, Order, OrderItem, Shipment
from products.models import Product
from users.models import Address
from coupons.models import Coupon
from django.db import OperationalError, transaction

# ─── Tarif Pengiriman Per Kurir & Paket ────────────────────────────────────────
# Format: { 'KURIR': { 'PAKET': {'label': ..., 'rate_per_kg': ..., 'estimate': ...} } }
SHIPPING_PACKAGES = {
    'JNE': {
        'REG': {'label': 'REG (Reguler)', 'rate_per_kg': 9000, 'estimate': '2-5 hari kerja'},
        'YES': {'label': 'YES (Yakin Esok Sampai)', 'rate_per_kg': 22000, 'estimate': '1 hari kerja'},
        'OKE': {'label': 'OKE (Ongkos Kirim Ekonomis)', 'rate_per_kg': 7000, 'estimate': '5-7 hari kerja'},
    },
    'TIKI': {
        'REG': {'label': 'REG (Regular)', 'rate_per_kg': 10000, 'estimate': '2-4 hari kerja'},
        'ONS': {'label': 'ONS (Over Night Service)', 'rate_per_kg': 25000, 'estimate': '1 hari kerja'},
        'ECO': {'label': 'ECO (Economy)', 'rate_per_kg': 8000, 'estimate': '5-8 hari kerja'},
    },
    'POS': {
        'BIASA': {'label': 'Paket Biasa', 'rate_per_kg': 8000, 'estimate': '3-7 hari kerja'},
        'KILAT': {'label': 'Paket Kilat', 'rate_per_kg': 18000, 'estimate': '1-2 hari kerja'},
    },
}


def calculate_shipping_cost(courier: str, service: str, total_weight_grams: int) -> int:
    """Hitung ongkir berdasarkan kurir, paket, dan berat total (dalam gram)."""
    courier_data = SHIPPING_PACKAGES.get(courier.upper(), {})
    service_data = courier_data.get(service.upper(), None)

    if not service_data:
        # Fallback: rate default Rp 15.000/kg
        rate = 15000
    else:
        rate = service_data['rate_per_kg']

    weight_kg = max(1.0, total_weight_grams / 1000.0)
    return round(weight_kg * rate)


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
        coupon_code: str = None, shipping_service: str = None
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

        shipping_cost = calculate_shipping_cost(courier_upper, service_upper, total_weight)

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
