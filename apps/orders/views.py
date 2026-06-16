from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from products.models import Product
from users.models import Address
from coupons.models import Coupon
from .models import Cart, CartItem, Order, Wishlist, Shipment
from .services import CartService, OrderService, WishlistService
from payments.models import Payment

class CartDetailView(TemplateView):
    template_name = 'cart/cart_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = CartService()
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        
        cart = service.get_cart(user=self.request.user if self.request.user.is_authenticated else None, session_key=session_key)
        context['cart'] = cart
        context['items'] = cart.items.all().select_related('product')
        return context


class AddToCartView(View):
    def post(self, request, product_id):
        service = CartService()
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart = service.get_cart(user=request.user if request.user.is_authenticated else None, session_key=session_key)
        quantity = int(request.POST.get('quantity', 1))

        try:
            service.add_item(cart, product_id, quantity)
            messages.success(request, "Produk berhasil ditambahkan ke keranjang belanja.")
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('cart_detail')


class UpdateCartItemView(View):
    def post(self, request, product_id):
        service = CartService()
        session_key = request.session.session_key
        cart = service.get_cart(user=request.user if request.user.is_authenticated else None, session_key=session_key)
        quantity = int(request.POST.get('quantity'))

        try:
            service.update_quantity(cart, product_id, quantity)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            messages.success(request, "Keranjang belanja diperbarui.")
        except ValueError as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, str(e))

        return redirect('cart_detail')


class RemoveCartItemView(View):
    def post(self, request, product_id):
        service = CartService()
        session_key = request.session.session_key
        cart = service.get_cart(user=request.user if request.user.is_authenticated else None, session_key=session_key)
        
        service.remove_item(cart, product_id)
        messages.success(request, "Produk dihapus dari keranjang.")
        return redirect('cart_detail')


class CheckoutView(LoginRequiredMixin, View):
    def get(self, request):
        service = CartService()
        cart = service.get_cart(user=request.user)
        if cart.items.count() == 0:
            messages.warning(request, "Keranjang Anda kosong.")
            return redirect('cart_detail')

        addresses = Address.objects.filter(user=request.user)
        active_address = addresses.filter(is_default=True).first() or addresses.first()
        couriers = Shipment.Courier.choices

        return render(request, 'checkout/checkout.html', {
            'cart': cart,
            'items': cart.items.all(),
            'addresses': addresses,
            'active_address': active_address,
            'couriers': couriers
        })

    def post(self, request):
        address_id = request.POST.get('address_id')
        courier = request.POST.get('courier')
        coupon_code = request.POST.get('coupon_code')

        cart_service = CartService()
        cart = cart_service.get_cart(user=request.user)

        try:
            address = Address.objects.get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, "Alamat pengiriman tidak valid.")
            return redirect('checkout')

        order_service = OrderService()
        try:
            order = order_service.checkout(
                user=request.user,
                cart=cart,
                address=address,
                courier=courier,
                coupon_code=coupon_code
            )
            messages.success(request, "Pesanan berhasil dibuat!")
            return redirect('order_detail', order_number=order.order_number)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('checkout')


class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_history.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    slug_field = 'order_number'
    slug_url_kwarg = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        context['items'] = order.items.all().select_related('product')
        context['payment_methods'] = Payment.Method.choices
        context['has_payment'] = Payment.objects.filter(order=order, status='SUCCESS').exists()
        return context


class CancelOrderView(LoginRequiredMixin, View):
    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.status == Order.Status.PENDING:
            # Revert stock
            for item in order.items.all():
                item.product.stock += item.quantity
                item.product.save()
            order.status = Order.Status.CANCELLED
            order.save()
            messages.success(request, "Pesanan dibatalkan.")
        else:
            messages.error(request, "Pesanan tidak dapat dibatalkan.")
        return redirect('order_detail', order_number=order.order_number)


class DownloadInvoiceView(LoginRequiredMixin, View):
    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if not hasattr(order, 'invoice') or not order.invoice.pdf_file:
            raise Http404("Invoice belum tersedia.")
        response = FileResponse(order.invoice.pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice-{order.order_number}.pdf"'
        return response


class WishlistListView(LoginRequiredMixin, TemplateView):
    template_name = 'auth/wishlist.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wishlist, _ = Wishlist.objects.get_or_create(user=self.request.user)
        context['products'] = wishlist.products.filter(is_active=True).prefetch_related('images')
        return context


class WishlistToggleView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        service = WishlistService()
        try:
            added = service.toggle_wishlist(request.user, product_id)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'added': added})
            messages.success(request, "Wishlist diperbarui.")
        except ValueError as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=400)
            messages.error(request, str(e))

        return redirect('product_list')
