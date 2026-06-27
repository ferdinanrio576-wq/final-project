from django.urls import path
from .views import ProductListView, ProductDetailView, AddReviewView

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:product_id>/review/', AddReviewView.as_view(), name='add_review'),
]
