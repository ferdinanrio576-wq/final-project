from .repositories import ProductRepository, ReviewRepository
from .models import Product, Review
from django.db.models import QuerySet


class ProductService:
    def __init__(self):
        self.product_repo = ProductRepository()

    def get_product_details(self, slug: str) -> Product:
        return self.product_repo.get_by_slug(slug)

    def get_featured_products(self, limit: int = 8) -> QuerySet:
        return self.product_repo.list_active().filter(is_featured=True)[:limit]

    def get_new_arrivals(self, limit: int = 8) -> QuerySet:
        return self.product_repo.list_active().order_by('-created_at')[:limit]


class ReviewService:
    def __init__(self):
        self.review_repo = ReviewRepository()

    def add_review(self, user, product_id: int, rating: int, comment: str, image=None) -> Review:
        # Ambil produk — fix bug: gunakan static method dengan benar
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ValueError("Produk tidak ditemukan.")

        # Cegah duplikat review (1 user hanya boleh review 1x per produk)
        if Review.objects.filter(user=user, product=product).exists():
            raise ValueError("Anda sudah pernah memberikan ulasan untuk produk ini.")

        # Cek apakah user sudah pernah membeli produk ini dan status pesanan sudah sah
        from orders.models import Order
        valid_purchase_statuses = [
            Order.Status.PAID,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.COMPLETED,
        ]
        has_purchased = Order.objects.filter(
            user=user,
            status__in=valid_purchase_statuses,
            items__product=product
        ).exists()

        if not has_purchased:
            raise ValueError(
                "Anda harus membeli dan menyelesaikan transaksi produk ini terlebih dahulu "
                "sebelum dapat memberikan ulasan."
            )

        return self.review_repo.create_review(
            user=user,
            product=product,
            rating=rating,
            comment=comment,
            image=image,
            is_verified=True  # Selalu True karena sudah divalidasi di atas
        )
