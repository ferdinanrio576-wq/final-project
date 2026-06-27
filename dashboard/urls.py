from django.urls import path
from .views import (
    DashboardIndexView, AdminProductListView, AdminProductCreateView,
    AdminProductUpdateView, AdminProductDeleteView, AdminCategoryListView,
    AdminCategoryCreateView, AdminCategoryUpdateView, AdminBrandListView,
    AdminBrandCreateView, AdminBrandUpdateView, AdminBrandDeleteView,
    AdminCouponListView, AdminCouponCreateView, AdminCouponUpdateView,
    AdminOrderListView, AdminOrderDetailView, AdminVerifyPaymentView, AdminUserListView,
    AdminUserUpdateView, AdminUserDeleteView, ReportsView, ExportReportView
)

urlpatterns = [
    path('', DashboardIndexView.as_view(), name='dashboard_index'),
    
    # Product CRUD
    path('products/', AdminProductListView.as_view(), name='admin_product_list'),
    path('products/add/', AdminProductCreateView.as_view(), name='admin_product_add'),
    path('products/<int:pk>/edit/', AdminProductUpdateView.as_view(), name='admin_product_edit'),
    path('products/<int:pk>/delete/', AdminProductDeleteView.as_view(), name='admin_product_delete'),
    
    # Category CRUD
    path('categories/', AdminCategoryListView.as_view(), name='admin_category_list'),
    path('categories/add/', AdminCategoryCreateView.as_view(), name='admin_category_add'),
    path('categories/<int:pk>/edit/', AdminCategoryUpdateView.as_view(), name='admin_category_edit'),

    # Brand CRUD
    path('brands/', AdminBrandListView.as_view(), name='admin_brand_list'),
    path('brands/add/', AdminBrandCreateView.as_view(), name='admin_brand_add'),
    path('brands/<int:pk>/edit/', AdminBrandUpdateView.as_view(), name='admin_brand_edit'),
    path('brands/<int:pk>/delete/', AdminBrandDeleteView.as_view(), name='admin_brand_delete'),
    
    # Coupon CRUD
    path('coupons/', AdminCouponListView.as_view(), name='admin_coupon_list'),
    path('coupons/add/', AdminCouponCreateView.as_view(), name='admin_coupon_add'),
    path('coupons/<int:pk>/edit/', AdminCouponUpdateView.as_view(), name='admin_coupon_edit'),
    
    # Order Updates
    path('orders/', AdminOrderListView.as_view(), name='admin_order_list'),
    path('orders/<int:pk>/detail/', AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('orders/<int:pk>/verify-payment/', AdminVerifyPaymentView.as_view(), name='admin_order_verify_payment'),
    
    # User Management
    path('users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('users/<int:pk>/edit/', AdminUserUpdateView.as_view(), name='admin_user_edit'),
    path('users/<int:pk>/delete/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
    
    # Reports Export
    path('reports/', ReportsView.as_view(), name='admin_reports'),
    path('reports/export/', ExportReportView.as_view(), name='admin_reports_export'),
]
