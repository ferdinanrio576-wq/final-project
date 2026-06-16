from .repositories import ProductRepository, ReviewRepository
from .models import Product, Review
from django.db.models import QuerySet

class ProductService:
    def __init__(self):
        self.product_repo = ProductRepository()

    def get_product_details(self, slug: str) -> Product:
        return self.product_repo.get_by_slug(slug)

    def get_related_products(self, product: Product, limit: int = 4) -> QuerySet:
        return self.product_repo.list_active().filter(category=product.category).exclude(id=product.id)[:limit]

    def get_featured_products(self, limit: int = 8) -> QuerySet:
        return self.product_repo.list_active().filter(is_featured=True)[:limit]

    def get_new_arrivals(self, limit: int = 8) -> QuerySet:
        return self.product_repo.list_active().order_by('-created_at')[:limit]


class ReviewService:
    def __init__(self):
        self.review_repo = ReviewRepository()

    def add_review(self, user, product_id: int, rating: int, comment: str, image=None) -> Review:
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ValueError("Produk tidak ditemukan.")

        # Check if user has a verified purchase
        # Import dynamically to avoid circular import issues
        from orders.models import Order
        
        has_purchased = Order.objects.filter(
            user=user,
            status='COMPLETED',
            items__product=product
        ).exists()

        return self.review_repo.create_review(
            user=user, 
            product=product, 
            rating=rating, 
            comment=comment, 
            image=image, 
            is_verified=has_purchased
        )
