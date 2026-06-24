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
from .services import CartService, OrderService, WishlistService, SHIPPING_PACKAGES, calculate_shipping_cost
from payments.models import Payment
from django.conf import settings


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

        # Hitung berat total keranjang untuk estimasi awal ongkir
        total_weight = sum(
            item.product.weight_grams * item.quantity
            for item in cart.items.all()
        )

        # Get active coupons to display
        from django.utils import timezone
        from coupons.models import Coupon
        coupons = Coupon.objects.filter(is_active=True).order_by('min_spend')
        
        coupons_data = []
        subtotal = cart.subtotal
        for coupon in coupons:
            is_valid = coupon.is_valid(request.user, subtotal)
            kuota_habis = coupon.active_limit is not None and coupon.used_count >= coupon.active_limit
            expired = coupon.expiry_date and coupon.expiry_date < timezone.now().date()
            
            reason = ""
            if expired:
                reason = "Voucher telah kadaluwarsa"
            elif kuota_habis:
                reason = "Kuota voucher telah habis"
            elif subtotal < coupon.min_spend:
                diff = coupon.min_spend - subtotal
                reason = f"Kurang belanja Rp {diff:,.0f}".replace(',', '.')
                
            coupons_data.append({
                'coupon': coupon,
                'is_valid': is_valid and not kuota_habis and not expired,
                'reason': reason,
                'formatted_min_spend': f"Rp {coupon.min_spend:,.0f}".replace(',', '.'),
                'formatted_max_discount': f"Rp {coupon.max_discount_amount:,.0f}".replace(',', '.') if coupon.max_discount_amount else "Tanpa batas",
            })

        return render(request, 'checkout/checkout.html', {
            'cart': cart,
            'items': cart.items.all(),
            'addresses': addresses,
            'active_address': active_address,
            'couriers': couriers,
            'shipping_packages': SHIPPING_PACKAGES,
            'total_weight_grams': total_weight,
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
            'coupons': coupons_data,
        })

    def post(self, request):
        address_id = request.POST.get('address_id')
        courier = request.POST.get('courier')
        shipping_service = request.POST.get('shipping_service', 'REG')
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
                coupon_code=coupon_code,
                shipping_service=shipping_service,
                destination_province=address.province,
            )
            messages.success(request, "Pesanan berhasil dibuat!")
            return redirect('order_detail', order_number=order.order_number)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('checkout')


class ShippingCostAPIView(View):
    """AJAX endpoint untuk kalkulasi ongkir real-time."""
    def get(self, request):
        courier = request.GET.get('courier', 'JNE').upper()
        service = request.GET.get('service', 'REG').upper()
        weight_grams = int(request.GET.get('weight', 1000))
        destination_province = request.GET.get('province')
        
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        address_id = request.GET.get('address_id')

        # Bersihkan string kosong atau 'undefined' atau 'null'
        if latitude in ('', 'null', 'undefined'):
            latitude = None
        if longitude in ('', 'null', 'undefined'):
            longitude = None

        if address_id and (latitude is None or longitude is None):
            try:
                from users.models import Address
                if request.user.is_authenticated:
                    address = Address.objects.filter(id=address_id, user=request.user).first()
                else:
                    address = Address.objects.filter(id=address_id).first()
                if address:
                    latitude = address.latitude
                    longitude = address.longitude
                    if not destination_province:
                        destination_province = address.province
            except Exception:
                pass

        # Ubah ke float jika ada
        if latitude is not None:
            try:
                latitude = float(latitude)
            except ValueError:
                latitude = None
        if longitude is not None:
            try:
                longitude = float(longitude)
            except ValueError:
                longitude = None

        cost = calculate_shipping_cost(
            courier=courier,
            service=service,
            total_weight_grams=weight_grams,
            destination_province=destination_province,
            latitude=latitude,
            longitude=longitude
        )

        courier_data = SHIPPING_PACKAGES.get(courier, {})
        service_data = courier_data.get(service, {})

        return JsonResponse({
            'cost': cost,
            'cost_formatted': f"Rp {cost:,.0f}".replace(',', '.'),
            'estimate': service_data.get('estimate', '-'),
            'label': service_data.get('label', service),
        })


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
        context['has_payment'] = Payment.objects.filter(order=order, status='SUCCESS').exists()
        # Ambil payment terbaru untuk tampil info bank
        context['latest_payment'] = Payment.objects.filter(order=order).order_by('-created_at').first()
        return context


class CancelOrderView(LoginRequiredMixin, View):
    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.status == Order.Status.PENDING:
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
        response = FileResponse(order.invoice.pdf_file.open('rb'), content_type='application/pdf')
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
