from rest_framework import viewsets, status, permissions, decorators
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

# Import Models
from users.models import Address, Profile
from products.models import Product, Category, Brand, Review
from orders.models import Cart, CartItem, Order, Wishlist
from coupons.models import Coupon
from notifications.models import Notification

# Import Serializers
from .serializers import (
    UserSerializer, RegisterSerializer, AddressSerializer, ProfileSerializer,
    ProductSerializer, CategorySerializer, BrandSerializer, ReviewSerializer,
    CartSerializer, CartItemSerializer, OrderSerializer, CouponSerializer,
    NotificationSerializer, PaymentSerializer
)

# Import Services
from users.services import UserService, AddressService
from products.services import ProductService, ReviewService
from orders.services import CartService, OrderService, WishlistService
from coupons.services import CouponService
from payments.services import PaymentService, InvoiceService
from notifications.services import NotificationService

User = get_user_model()

# ==========================================
# AUTHENTICATION & USER VIEWSET
# ==========================================

class AuthViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @decorators.action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            service = UserService()
            user = service.register_customer(
                email=serializer.validated_data['email'],
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated], url_path='profile')
    def profile(self, request):
        user = request.user
        if request.method == 'GET':
            return Response(UserSerializer(user).data)
            
        service = UserService()
        profile_data = request.data
        
        avatar = request.FILES.get('avatar', None)
        profile = service.update_profile(
            user=user,
            phone_number=profile_data.get('phone_number'),
            avatar=avatar,
            birth_date=profile_data.get('birth_date'),
            gender=profile_data.get('gender')
        )
        return Response(UserSerializer(user).data)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

    def perform_create(self, serializer):
        service = AddressService()
        service.add_address(
            user=self.request.user,
            label=serializer.validated_data.get('label', 'Rumah'),
            recipient_name=serializer.validated_data['recipient_name'],
            phone_number=serializer.validated_data['phone_number'],
            street_address=serializer.validated_data['street_address'],
            city=serializer.validated_data['city'],
            province=serializer.validated_data['province'],
            postal_code=serializer.validated_data['postal_code'],
            is_default=serializer.validated_data.get('is_default', False)
        )

    @decorators.action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        service = AddressService()
        success = service.set_default(pk, request.user)
        if success:
            return Response({'status': 'address set to default'})
        return Response({'error': 'address not found'}, status=status.HTTP_404_NOT_FOUND)


# ==========================================
# PRODUCT CATALOG VIEWSET
# ==========================================

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        from products.repositories import ProductRepository
        queryset = ProductRepository.list_active()
        
        # Apply filters
        search_query = self.request.query_params.get('search')
        category_slug = self.request.query_params.get('category')
        brand_slug = self.request.query_params.get('brand')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        sort_by = self.request.query_params.get('sort_by')
        
        if min_price:
            min_price = float(min_price)
        if max_price:
            max_price = float(max_price)

        return ProductRepository.filter_and_search(
            queryset, search_query, category_slug, brand_slug, min_price, max_price, sort_by
        )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]


# ==========================================
# CART & WISHLIST VIEWSET
# ==========================================

class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def _get_session_key(self, request):
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key

    def retrieve(self, request):
        service = CartService()
        session_key = self._get_session_key(request)
        cart = service.get_cart(user=request.user, session_key=session_key)
        return Response(CartSerializer(cart).data)

    @decorators.action(detail=False, methods=['post'], url_path='add')
    def add_item(self, request):
        service = CartService()
        session_key = self._get_session_key(request)
        cart = service.get_cart(user=request.user, session_key=session_key)
        
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        try:
            item = service.add_item(cart, product_id, quantity)
            return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(detail=False, methods=['post'], url_path='update')
    def update_item(self, request):
        service = CartService()
        session_key = self._get_session_key(request)
        cart = service.get_cart(user=request.user, session_key=session_key)

        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity'))

        try:
            item = service.update_quantity(cart, product_id, quantity)
            return Response(CartItemSerializer(item).data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(detail=False, methods=['post'], url_path='remove')
    def remove_item(self, request):
        service = CartService()
        session_key = self._get_session_key(request)
        cart = service.get_cart(user=request.user, session_key=session_key)

        product_id = request.data.get('product_id')
        service.remove_item(cart, product_id)
        return Response({'status': 'item removed'}, status=status.HTTP_200_OK)


class WishlistViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        serializer = ProductSerializer(wishlist.products.all(), many=True)
        return Response(serializer.data)

    @decorators.action(detail=False, methods=['post'], url_path='toggle')
    def toggle(self, request):
        product_id = request.data.get('product_id')
        service = WishlistService()
        try:
            added = service.toggle_wishlist(request.user, product_id)
            return Response({'status': 'success', 'added': added})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# ORDER VIEWSET & CHECKOUT
# ==========================================

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request):
        # Checkout Endpoint
        address_id = request.data.get('address_id')
        courier = request.data.get('courier')
        coupon_code = request.data.get('coupon_code')

        cart_service = CartService()
        cart = cart_service.get_cart(user=request.user)

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({'error': 'Alamat pengiriman tidak valid.'}, status=status.HTTP_400_BAD_REQUEST)

        order_service = OrderService()
        try:
            order = order_service.checkout(
                user=request.user,
                cart=cart,
                address=address,
                courier=courier,
                coupon_code=coupon_code
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_210_CREATED if hasattr(status, 'HTTP_210_CREATED') else status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# PAYMENT GATEWAY SIMULATION & CALLBACKS
# ==========================================

class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @decorators.action(detail=True, methods=['post'], url_path='pay-simulated')
    def pay_simulated(self, request, pk=None):
        """
        Simulates customer payment completion
        """
        order = get_object_or_404(Order, id=pk, user=request.user)
        if order.status != Order.Status.PENDING:
            return Response({'error': 'Pesanan sudah dibayar atau dibatalkan.'}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = request.data.get('payment_method', Payment.Method.MIDTRANS)
        
        # Process payment simulation
        pay_service = PaymentService()
        payment = pay_service.process_payment_simulation(order, payment_method)
        
        # Auto-trigger payment success for simulation
        pay_service.verify_payment(
            transaction_id=payment.transaction_id,
            success=True,
            payload={'method': payment_method, 'gateway_response': 'MOCK_SUCCESS'}
        )

        return Response({
            'status': 'success',
            'order_number': order.order_number,
            'transaction_id': payment.transaction_id,
            'message': 'Pembayaran berhasil disimulasikan.'
        })


# ==========================================
# REVIEWS VIEWSET
# ==========================================

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        product_id = self.request.query_params.get('product')
        if product_id:
            return Review.objects.filter(product_id=product_id).order_by('-created_at')
        return Review.objects.all().order_by('-created_at')

    def create(self, request):
        product_id = request.data.get('product')
        rating = int(request.data.get('rating'))
        comment = request.data.get('comment')
        image = request.FILES.get('image', None)

        service = ReviewService()
        try:
            review = service.add_review(
                user=request.user,
                product_id=product_id,
                rating=rating,
                comment=comment,
                image=image
            )
            return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# NOTIFICATION & VOUCHER VIEWSET
# ==========================================

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @decorators.action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        service = NotificationService()
        service.mark_all_as_read(request.user)
        return Response({'status': 'all notifications marked as read'})


class CouponViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @decorators.action(detail=False, methods=['post'], url_path='validate')
    def validate_coupon(self, request):
        code = request.data.get('code')
        subtotal = float(request.data.get('subtotal', 0))

        service = CouponService()
        is_valid, discount_amount, message = service.validate_coupon(code, request.user, subtotal)
        
        if is_valid:
            return Response({
                'valid': True,
                'discount_amount': discount_amount,
                'message': message
            })
        return Response({
            'valid': False,
            'discount_amount': 0,
            'message': message
        }, status=status.HTTP_400_BAD_REQUEST)
