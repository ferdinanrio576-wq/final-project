from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    AuthViewSet, AddressViewSet, ProductViewSet, CategoryViewSet,
    BrandViewSet, CartViewSet, WishlistViewSet, OrderViewSet,
    PaymentViewSet, ReviewViewSet, NotificationViewSet, CouponViewSet
)

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='api-addresses')
router.register(r'products', ProductViewSet, basename='api-products')
router.register(r'categories', CategoryViewSet, basename='api-categories')
router.register(r'brands', BrandViewSet, basename='api-brands')
router.register(r'wishlist', WishlistViewSet, basename='api-wishlist')
router.register(r'orders', OrderViewSet, basename='api-orders')
router.register(r'reviews', ReviewViewSet, basename='api-reviews')
router.register(r'notifications', NotificationViewSet, basename='api-notifications')

# Customize views for actions with no queryset
auth_list = AuthViewSet.as_view({'post': 'register'})
auth_profile = AuthViewSet.as_view({
    'get': 'profile',
    'put': 'profile',
    'patch': 'profile'
})

cart_retrieve = CartViewSet.as_view({'get': 'retrieve'})
cart_add = CartViewSet.as_view({'post': 'add_item'})
cart_update = CartViewSet.as_view({'post': 'update_item'})
cart_remove = CartViewSet.as_view({'post': 'remove_item'})

coupon_validate = CouponViewSet.as_view({'post': 'validate_coupon'})

urlpatterns = [
    # JWT Token authentication endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Custom Non-CRUD endpoint routing
    path('auth/register/', auth_list, name='api-register'),
    path('auth/profile/', auth_profile, name='api-profile'),
    
    path('cart/', cart_retrieve, name='api-cart-get'),
    path('cart/add/', cart_add, name='api-cart-add'),
    path('cart/update/', cart_update, name='api-cart-update'),
    path('cart/remove/', cart_remove, name='api-cart-remove'),
    
    path('coupons/validate/', coupon_validate, name='api-coupon-validate'),
    
    path('payments/<int:pk>/pay-simulated/', PaymentViewSet.as_view({'post': 'pay_simulated'}), name='api-pay-simulated'),
    
    # Standard router endpoints
    path('', include(router.urls)),
]
