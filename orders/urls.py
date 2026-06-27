from django.urls import path
from .views import (
    CartDetailView, AddToCartView, UpdateCartItemView, RemoveCartItemView,
    CheckoutView, OrderHistoryView, OrderDetailView, CancelOrderView,
    DownloadInvoiceView, WishlistListView, WishlistToggleView,
    ShippingCostAPIView
)

urlpatterns = [
    path('', CartDetailView.as_view(), name='cart_detail'),
    path('add/<int:product_id>/', AddToCartView.as_view(), name='cart_add'),
    path('update/<int:product_id>/', UpdateCartItemView.as_view(), name='cart_update'),
    path('remove/<int:product_id>/', RemoveCartItemView.as_view(), name='cart_remove'),

    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('history/', OrderHistoryView.as_view(), name='order_history'),
    path('details/<str:order_number>/', OrderDetailView.as_view(), name='order_detail'),
    path('cancel/<str:order_number>/', CancelOrderView.as_view(), name='order_cancel'),
    path('invoice/<str:order_number>/', DownloadInvoiceView.as_view(), name='download_invoice'),

    path('wishlist/', WishlistListView.as_view(), name='wishlist_list'),
    path('wishlist/toggle/<int:product_id>/', WishlistToggleView.as_view(), name='wishlist_toggle'),

    # AJAX endpoint untuk kalkulasi ongkir dinamis
    path('api/shipping-cost/', ShippingCostAPIView.as_view(), name='shipping_cost_api'),
]
