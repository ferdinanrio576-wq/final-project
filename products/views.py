from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Product, Category, Brand, Review
from .repositories import ProductRepository
from .services import ProductService, ReviewService


class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        repo = ProductRepository()
        queryset = repo.list_active()

        # Retrieve filters from GET request
        self.search_query = self.request.GET.get('search', '')
        self.category_slug = self.request.GET.get('category', '')
        self.brand_slug = self.request.GET.get('brand', '')
        self.min_price = self.request.GET.get('min_price')
        self.max_price = self.request.GET.get('max_price')
        self.sort_by = self.request.GET.get('sort_by', '')

        min_val = float(self.min_price) if self.min_price else None
        max_val = float(self.max_price) if self.max_price else None

        return repo.filter_and_search(
            queryset, self.search_query, self.category_slug, self.brand_slug, min_val, max_val, self.sort_by
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.search_query
        context['category_slug'] = self.category_slug
        context['brand_slug'] = self.brand_slug
        context['min_price'] = self.min_price or ''
        context['max_price'] = self.max_price or ''
        context['sort_by'] = self.sort_by

        service = ProductService()
        context['featured_products'] = service.get_featured_products(4)
        context['new_arrivals'] = service.get_new_arrivals(4)
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'
    lookup_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()

        context['specifications'] = product.specifications.all()
        context['images'] = product.images.all()
        context['reviews'] = product.reviews.select_related('user').order_by('-created_at')

        # Wishlist status check
        if self.request.user.is_authenticated:
            from orders.models import Wishlist, Order
            wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
            context['in_wishlist'] = product in wishlist.products.all()

            # Cek apakah user sudah memiliki status pesanan yang valid untuk review
            valid_purchase_statuses = [
                Order.Status.PAID,
                Order.Status.PROCESSING,
                Order.Status.SHIPPED,
                Order.Status.COMPLETED,
            ]
            user_can_review = Order.objects.filter(
                user=self.request.user,
                status__in=valid_purchase_statuses,
                items__product=product
            ).exists()
            context['user_can_review'] = user_can_review

            # Cek apakah user sudah pernah memberi review
            user_already_reviewed = Review.objects.filter(
                user=self.request.user,
                product=product
            ).exists()
            context['user_already_reviewed'] = user_already_reviewed
        else:
            context['in_wishlist'] = False
            context['user_can_review'] = False
            context['user_already_reviewed'] = False

        return context


class AddReviewView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        rating_str = request.POST.get('rating', '5')
        comment = request.POST.get('comment', '').strip()
        image = request.FILES.get('image', None)

        product = get_object_or_404(Product, id=product_id)

        try:
            rating = int(rating_str)
            if not 1 <= rating <= 5:
                raise ValueError("Rating harus antara 1 sampai 5.")
        except (ValueError, TypeError):
            messages.error(request, "Rating tidak valid.")
            return redirect('product_detail', slug=product.slug)

        if not comment:
            messages.error(request, "Isi ulasan tidak boleh kosong.")
            return redirect('product_detail', slug=product.slug)

        service = ReviewService()
        try:
            service.add_review(
                user=request.user,
                product_id=product_id,
                rating=rating,
                comment=comment,
                image=image
            )
            messages.success(request, "Ulasan Anda berhasil dikirim! Terima kasih.")
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('product_detail', slug=product.slug)
