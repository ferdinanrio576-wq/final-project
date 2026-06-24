from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

from users.models import Address
from products.models import Product, Category, Brand
from orders.models import Cart, CartItem, Order, OrderItem
from coupons.models import Coupon
from orders.services import CartService, OrderService
from coupons.services import CouponService

User = get_user_model()

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ECommerceServiceTestCase(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='test@email.com',
            username='testuser',
            password='testpassword',
            role=User.Role.CUSTOMER
        )
        
        # Create category & brand
        self.category = Category.objects.create(name='Gadget', slug='gadget')
        self.brand = Brand.objects.create(name='Macrohard', slug='macrohard')
        
        # Create product
        self.product = Product.objects.create(
            name='Laptop Pro',
            sku='LAP-001',
            description='Laptop description',
            price=10000000.00,
            stock=10,
            weight_grams=1500,
            category=self.category,
            brand=self.brand
        )

        # Create address
        self.address = Address.objects.create(
            user=self.user,
            recipient_name='Test Recipient',
            phone_number='0812345678',
            street_address='Jl. Test No. 1',
            city='Jakarta',
            province='DKI Jakarta',
            postal_code='12345'
        )

        # Create coupon
        self.coupon = Coupon.objects.create(
            code='DISKON10',
            discount_percentage=10,
            max_discount_amount=1000000.00,
            min_spend=5000000.00,
            expiry_date=timezone.now().date() + datetime.timedelta(days=7),
            is_active=True
        )

    def test_cart_service_flow(self):
        cart_service = CartService()
        cart = cart_service.get_cart(user=self.user)
        
        # Test add item
        item = cart_service.add_item(cart, self.product.id, quantity=2)
        self.assertEqual(cart.total_items, 2)
        self.assertEqual(cart.subtotal, 20000000.00)

        # Test update quantity
        cart_service.update_quantity(cart, self.product.id, quantity=5)
        self.assertEqual(cart.total_items, 5)
        self.assertEqual(cart.subtotal, 50000000.00)

        # Test remove item
        cart_service.remove_item(cart, self.product.id)
        self.assertEqual(cart.total_items, 0)

    def test_coupon_service_validation(self):
        # 1. Valid coupon check
        is_valid, discount, msg = CouponService.validate_coupon('DISKON10', self.user, 10000000.00)
        self.assertTrue(is_valid)
        self.assertEqual(discount, 1000000.00) # 10% of 10M is 1M

        # 2. Coupon below min spend check
        is_valid, discount, msg = CouponService.validate_coupon('DISKON10', self.user, 3000000.00)
        self.assertFalse(is_valid)
        self.assertEqual(discount, 0)

    def test_order_checkout_flow(self):
        cart_service = CartService()
        cart = cart_service.get_cart(user=self.user)
        cart_service.add_item(cart, self.product.id, quantity=2) # 20M subtotal

        order_service = OrderService()
        order = order_service.checkout(
            user=self.user,
            cart=cart,
            address=self.address,
            courier='JNE',
            coupon_code='DISKON10'
        )

        # Verify order state
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.total_amount, 20000000.00)
        self.assertEqual(order.discount_amount, 1000000.00) # 1M discount
        
        # Verify unique payment code logic
        self.assertTrue(100 <= order.unique_code <= 999)
        expected_final = (order.total_amount + order.shipping_cost + order.tax_amount) - order.discount_amount
        self.assertEqual(order.payment_amount, expected_final + order.unique_code)

        # Verify product stock reduction
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8) # 10 - 2 = 8

        # Verify cart items cleared
        self.assertEqual(cart.items.count(), 0)
