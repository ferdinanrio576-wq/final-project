from .models import Product, Category, Brand, Review
from django.db.models import Q, QuerySet
from typing import Optional

class ProductRepository:
    @staticmethod
    def get_by_id(product_id: int) -> Optional[Product]:
        try:
            return Product.objects.select_related('brand', 'category').prefetch_related('images', 'specifications', 'reviews').get(id=product_id)
        except Product.DoesNotExist:
            return None

    @staticmethod
    def get_by_slug(slug: str) -> Optional[Product]:
        try:
            return Product.objects.select_related('brand', 'category').prefetch_related('images', 'specifications', 'reviews').get(slug=slug)
        except Product.DoesNotExist:
            return None

    @staticmethod
    def list_active() -> QuerySet:
        return Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')

    @staticmethod
    def filter_and_search(
        queryset: QuerySet, search_query: str = None, category_slug: str = None, 
        brand_slug: str = None, min_price: float = None, max_price: float = None, 
        sort_by: str = None
    ) -> QuerySet:
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) | 
                Q(sku__icontains=search_query)
            )

        if category_slug:
            # Matches category or subcategories
            queryset = queryset.filter(
                Q(category__slug=category_slug) | 
                Q(category__parent_category__slug=category_slug)
            )

        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)

        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        # Sorting logic
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-is_featured', '-created_at')

        return queryset


class CategoryRepository:
    @staticmethod
    def list_all() -> QuerySet:
        return Category.objects.all().order_by('name')

    @staticmethod
    def list_root_categories() -> QuerySet:
        return Category.objects.filter(parent_category__isnull=True).prefetch_related('subcategories')


class ReviewRepository:
    @staticmethod
    def get_product_reviews(product_id: int) -> QuerySet:
        return Review.objects.filter(product_id=product_id).select_related('user').order_by('-created_at')

    @staticmethod
    def create_review(user, product: Product, rating: int, comment: str, image=None, is_verified: bool = False) -> Review:
        return Review.objects.create(
            user=user, product=product, rating=rating, comment=comment, image=image, is_verified_purchase=is_verified
        )
