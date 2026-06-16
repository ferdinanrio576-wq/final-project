from .models import Cart, CartItem, Order, OrderItem, Shipment, Wishlist
from products.models import Product
from users.models import Address
from coupons.models import Coupon
from typing import Optional, Tuple
from django.db.models import QuerySet

class CartRepository:
    @staticmethod
    def get_user_cart(user) -> Tuple[Cart, bool]:
        return Cart.objects.get_or_create(user=user)

    @staticmethod
    def get_session_cart(session_key: str) -> Tuple[Cart, bool]:
        return Cart.objects.get_or_create(session_key=session_key)

    @staticmethod
    def merge_carts(session_cart: Cart, user_cart: Cart):
        # Move items from session cart to user cart
        for item in session_cart.items.all():
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=item.product,
                defaults={'quantity': item.quantity}
            )
            if not created:
                user_item.quantity += item.quantity
                user_item.save()
        session_cart.delete()


class OrderRepository:
    @staticmethod
    def get_by_number(order_number: str) -> Optional[Order]:
        try:
            return Order.objects.select_related('user', 'coupon', 'shipment').prefetch_related('items__product').get(order_number=order_number)
        except Order.DoesNotExist:
            return None

    @staticmethod
    def list_user_orders(user) -> QuerySet:
        return Order.objects.filter(user=user).select_related('shipment').prefetch_related('items__product').order_by('-created_at')

    @staticmethod
    def create_order(
        user, address: Address, total_amount: float, shipping_cost: float,
        tax_amount: float, discount_amount: float, unique_code: int, payment_amount: float,
        coupon: Optional[Coupon] = None
    ) -> Order:
        order = Order.objects.create(
            user=user,
            total_amount=total_amount,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            unique_code=unique_code,
            payment_amount=payment_amount,
            payment_status='UNPAID',
            shipping_address_label=address.label,
            shipping_recipient_name=address.recipient_name,
            shipping_phone_number=address.phone_number,
            shipping_street_address=address.street_address,
            shipping_city=address.city,
            shipping_province=address.province,
            shipping_postal_code=address.postal_code,
            coupon=coupon
        )
        return order


class WishlistRepository:
    @staticmethod
    def get_or_create_wishlist(user) -> Tuple[Wishlist, bool]:
        return Wishlist.objects.get_or_create(user=user)
