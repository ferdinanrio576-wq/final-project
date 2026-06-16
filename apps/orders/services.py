import time

from .repositories import CartRepository, OrderRepository, WishlistRepository
from .models import Cart, CartItem, Order, OrderItem, Shipment
from products.models import Product
from users.models import Address
from coupons.models import Coupon
from django.db import OperationalError, transaction

class CartService:
    def __init__(self):
        self.cart_repo = CartRepository()

    def get_cart(self, user=None, session_key: str = None) -> Cart:
        if user and user.is_authenticated:
            cart, _ = self.cart_repo.get_user_cart(user)
            # If session key has a cart, merge it
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
        coupon_code: str = None
    ) -> Order:
        if cart.items.count() == 0:
            raise ValueError("Keranjang belanja kosong.")

        # Validate stock before continuing
        for item in cart.items.all():
            if item.product.stock < item.quantity:
                raise ValueError(f"Stok produk '{item.product.name}' tidak mencukupi.")

        # Calculate costs
        subtotal = cart.subtotal
        
        from decimal import Decimal
        
        # Simulate shipping cost based on courier and product weights
        total_weight = sum(item.product.weight_grams * item.quantity for item in cart.items.all())
        # Base shipping rate: Rp 15.000 per kg
        weight_kg = max(1.0, total_weight / 1000.0)
        shipping_cost = round(weight_kg * 15000)
        
        # Tax calculation (11% of subtotal)
        tax_amount = round(subtotal * Decimal('0.11'))
        
        # Discount logic with Coupon
        discount_amount = 0
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code, is_active=True)
                if coupon.is_valid(user, subtotal):
                    discount_amount = round(subtotal * Decimal(coupon.discount_percentage) / Decimal('100'))
                    # Cap the discount
                    if coupon.max_discount_amount and discount_amount > coupon.max_discount_amount:
                        discount_amount = coupon.max_discount_amount
                    coupon.used_count += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass # invalid or expired coupon is ignored

        # Calculate final amount for unique code addition
        final_amount = (subtotal + Decimal(shipping_cost) + Decimal(tax_amount)) - Decimal(discount_amount)
        
        import random
        # Generate unique code with collision check
        max_attempts = 100
        unique_code = random.randint(100, 999)
        attempts = 0
        while Order.objects.filter(status__in=[Order.Status.PENDING, Order.Status.AWAITING_VERIFICATION], unique_code=unique_code).exists() and attempts < max_attempts:
            unique_code = random.randint(100, 999)
            attempts += 1

        payment_amount = final_amount + Decimal(unique_code)

        # Create Order
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

        # Create Order Items and decrease product stock
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.final_price,
                quantity=item.quantity
            )
            # Decrease stock
            item.product.stock -= item.quantity
            item.product.save()

        # Create Shipment record
        Shipment.objects.create(
            order=order,
            courier=courier,
            status=Shipment.Status.PENDING
        )

        # Clear Cart
        cart.items.all().delete()

        # Create notification in-app
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
            return False # removed
        else:
            wishlist.products.add(product)
            return True # added
