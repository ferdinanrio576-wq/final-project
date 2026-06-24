from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import Profile, Address
from products.models import Category, Brand, Product, ProductImage, ProductSpecification, Review
from orders.models import Cart, CartItem, Wishlist, Order, OrderItem, Shipment
from payments.models import Payment, Invoice
from coupons.models import Coupon
from notifications.models import Notification

User = get_user_model()

# ==========================================
# USER & PROFILE SERIALIZERS
# ==========================================

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['phone_number', 'avatar', 'birth_date', 'gender']


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'email_verified', 'is_banned', 'profile']
        read_only_fields = ['role', 'email_verified', 'is_banned']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.Role.CUSTOMER
        )
        return user


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'label', 'recipient_name', 'phone_number', 'street_address', 'city', 'province', 'postal_code', 'is_default']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


# ==========================================
# PRODUCT CATALOG SERIALIZERS
# ==========================================

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'parent_category']


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary']


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ['name', 'value']


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'description', 'price', 
            'discount_price', 'final_price', 'has_discount', 'stock', 
            'weight_grams', 'category', 'brand', 'is_active', 
            'is_featured', 'images', 'specifications', 'average_rating'
        ]


# ==========================================
# WISHLIST & REVIEWS SERIALIZERS
# ==========================================

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'rating', 'comment', 'image', 'is_verified_purchase', 'created_at']
        read_only_fields = ['id', 'is_verified_purchase', 'created_at']


# ==========================================
# CART SERIALIZERS
# ==========================================

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal']
        read_only_fields = ['id', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal']


# ==========================================
# COUPON SERIALIZERS
# ==========================================

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_percentage', 'max_discount_amount', 'min_spend', 'expiry_date', 'is_active']


# ==========================================
# ORDER & SHIPMENT SERIALIZERS
# ==========================================

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'price', 'quantity', 'subtotal']


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = ['courier', 'tracking_number', 'status', 'shipped_at', 'delivered_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipment = ShipmentSerializer(read_only=True)
    coupon = CouponSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'total_amount', 'shipping_cost', 
            'tax_amount', 'discount_amount', 'final_amount', 'shipping_address_label', 
            'shipping_recipient_name', 'shipping_phone_number', 'shipping_street_address', 
            'shipping_city', 'shipping_province', 'shipping_postal_code', 
            'coupon', 'items', 'shipment', 'created_at'
        ]
        read_only_fields = ['id', 'order_number', 'status', 'created_at']


# ==========================================
# PAYMENT & NOTIFICATION SERIALIZERS
# ==========================================

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'payment_method', 'transaction_id', 'status', 'amount', 'payment_date', 'created_at']
        read_only_fields = ['id', 'transaction_id', 'status', 'amount', 'payment_date', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
