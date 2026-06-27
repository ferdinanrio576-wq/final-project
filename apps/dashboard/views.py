import csv
import datetime
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, Http404, FileResponse
from django.utils import timezone
from io import BytesIO

from users.models import User
from products.models import Product, Category, Brand, ProductImage
from orders.models import Order, OrderItem, Shipment
from coupons.models import Coupon
from payments.models import Payment
from .forms import ProductForm, CategoryForm, BrandForm, CouponForm, OrderUpdateForm, UserManageForm

# Openpyxl for Excel export
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# xhtml2pdf for PDF export
try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin_user

    def handle_no_permission(self):
        messages.error(self.request, "Akses ditolak. Halaman ini hanya untuk Administrator.")
        return redirect('login')


# ==========================================
# DASHBOARD INDEX
# ==========================================

class DashboardIndexView(AdminRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Core Statistics
        paid_orders = Order.objects.filter(status__in=[Order.Status.PAID, Order.Status.SHIPPED, Order.Status.COMPLETED])
        context['total_revenue'] = paid_orders.aggregate(r=Sum('total_amount'))['r'] or 0.0
        
        context['total_orders'] = Order.objects.count()
        context['total_products'] = Product.objects.count()
        context['total_customers'] = User.objects.filter(role=User.Role.CUSTOMER).count()
        
        # Recent orders
        context['recent_orders'] = Order.objects.all().order_by('-created_at')[:5]
        
        # Best selling products
        context['best_sellers'] = OrderItem.objects.values(
            'product__name', 'product__sku'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]

        # Monthly Sales Data for Chart.js (Last 6 Months)
        monthly_sales = []
        months_label = []
        now = timezone.now()
        for i in range(5, -1, -1):
            date = now - datetime.timedelta(days=i*30)
            month_start = date.replace(day=1, hour=0, minute=0, second=0)
            # Find next month
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year+1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month+1)
            
            sales_val = Order.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end,
                status__in=[Order.Status.PAID, Order.Status.SHIPPED, Order.Status.COMPLETED]
            ).aggregate(s=Sum('total_amount'))['s'] or 0.0
            
            monthly_sales.append(float(sales_val))
            months_label.append(month_start.strftime('%B %Y'))

        context['chart_labels'] = months_label
        context['chart_data'] = monthly_sales
        
        return context


# ==========================================
# PRODUCT MANAGEMENT CRUD
# ==========================================

class AdminProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = 'dashboard/product_list.html'
    context_object_name = 'products'
    paginate_by = 10
    ordering = ['-created_at']


class AdminProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'dashboard/product_form.html'
    success_url = reverse_lazy('admin_product_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        image = form.cleaned_data.get('product_image')
        if image:
            from products.models import ProductImage
            ProductImage.objects.create(product=self.object, image=image, is_primary=True)
        messages.success(self.request, "Produk berhasil ditambahkan.")
        return response


class AdminProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'dashboard/product_form.html'
    success_url = reverse_lazy('admin_product_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        image = form.cleaned_data.get('product_image')
        if image:
            from products.models import ProductImage
            primary_img = self.object.images.filter(is_primary=True).first()
            if primary_img:
                primary_img.image = image
                primary_img.save()
            else:
                ProductImage.objects.create(product=self.object, image=image, is_primary=True)
        messages.success(self.request, "Produk berhasil diperbarui.")
        return response


class AdminProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    success_url = reverse_lazy('admin_product_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Produk berhasil dihapus.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# CATEGORY & BRAND MANAGEMENT CRUD
# ==========================================

class AdminCategoryListView(AdminRequiredMixin, ListView):
    model = Category
    template_name = 'dashboard/category_list.html'
    context_object_name = 'categories'


class AdminCategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/category_form.html'
    success_url = reverse_lazy('admin_category_list')

    def form_valid(self, form):
        messages.success(self.request, "Kategori berhasil ditambahkan.")
        return super().form_valid(form)


class AdminCategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'dashboard/category_form.html'
    success_url = reverse_lazy('admin_category_list')

    def form_valid(self, form):
        messages.success(self.request, "Kategori berhasil diperbarui.")
        return super().form_valid(form)


# ==========================================
# BRAND MANAGEMENT CRUD
# ==========================================

class AdminBrandListView(AdminRequiredMixin, ListView):
    model = Brand
    template_name = 'dashboard/brand_list.html'
    context_object_name = 'brands'
    paginate_by = 10
    ordering = ['-created_at'] if hasattr(Brand, 'created_at') else ['name']


class AdminBrandCreateView(AdminRequiredMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = 'dashboard/brand_form.html'
    success_url = reverse_lazy('admin_brand_list')

    def form_valid(self, form):
        messages.success(self.request, "Brand berhasil ditambahkan.")
        return super().form_valid(form)


class AdminBrandUpdateView(AdminRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = 'dashboard/brand_form.html'
    success_url = reverse_lazy('admin_brand_list')

    def form_valid(self, form):
        messages.success(self.request, "Brand berhasil diperbarui.")
        return super().form_valid(form)


class AdminBrandDeleteView(AdminRequiredMixin, DeleteView):
    model = Brand
    success_url = reverse_lazy('admin_brand_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Brand berhasil dihapus.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# COUPON MANAGEMENT CRUD
# ==========================================


class AdminCouponListView(AdminRequiredMixin, ListView):
    model = Coupon
    template_name = 'dashboard/coupon_list.html'
    context_object_name = 'coupons'
    ordering = ['-created_at']


class AdminCouponCreateView(AdminRequiredMixin, CreateView):
    model = Coupon
    form_class = CouponForm
    template_name = 'dashboard/coupon_form.html'
    success_url = reverse_lazy('admin_coupon_list')

    def form_valid(self, form):
        messages.success(self.request, "Voucher kupon berhasil dibuat.")
        return super().form_valid(form)


class AdminCouponUpdateView(AdminRequiredMixin, UpdateView):
    model = Coupon
    form_class = CouponForm
    template_name = 'dashboard/coupon_form.html'
    success_url = reverse_lazy('admin_coupon_list')

    def form_valid(self, form):
        messages.success(self.request, "Kupon berhasil diperbarui.")
        return super().form_valid(form)


# ==========================================
# ORDER MANAGEMENT
# ==========================================

class AdminOrderListView(AdminRequiredMixin, ListView):
    model = Order
    template_name = 'dashboard/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', '')
        return context


class AdminOrderDetailView(AdminRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, id=pk)
        form = OrderUpdateForm(instance=order, initial={
            'tracking_number': order.shipment.tracking_number if hasattr(order, 'shipment') else '',
            'shipment_status': order.shipment.status if hasattr(order, 'shipment') else 'PENDING'
        })
        return render(request, 'dashboard/order_detail.html', {
            'order': order,
            'items': order.items.all().select_related('product'),
            'form': form
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, id=pk)
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            
            # Update shipment detail
            shipment, created = Shipment.objects.get_or_create(order=order)
            tracking_number = form.cleaned_data.get('tracking_number')
            ship_status = form.cleaned_data.get('shipment_status')

            if ship_status in [Shipment.Status.SHIPPED, Shipment.Status.DELIVERED] and not tracking_number:
                tracking_number = f"TRK-{order.order_number.split('-')[-1]}-{uuid.uuid4().hex[:6].upper()}"

            shipment.tracking_number = tracking_number
            shipment.status = ship_status
            if ship_status == Shipment.Status.SHIPPED and not shipment.shipped_at:
                shipment.shipped_at = timezone.now()
            elif ship_status == Shipment.Status.DELIVERED and not shipment.delivered_at:
                shipment.delivered_at = timezone.now()
            shipment.save()

            # If shipment delivered, we can auto mark order as completed
            if ship_status == Shipment.Status.DELIVERED:
                order.status = Order.Status.COMPLETED

            order.save()
            messages.success(request, "Detail pesanan berhasil diperbarui.")
            return redirect('admin_order_detail', pk=order.id)
            
        return render(request, 'dashboard/order_detail.html', {
            'order': order,
            'items': order.items.all(),
            'form': form
        })


class AdminVerifyPaymentView(AdminRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, id=pk)
        
        if order.status != Order.Status.AWAITING_VERIFICATION:
            messages.error(request, "Pesanan tidak dalam status menunggu verifikasi.")
            return redirect('admin_order_detail', pk=order.id)
        
        payment = order.payments.filter(status=Payment.Status.PENDING).first()
        if not payment:
            import uuid
            transaction_id = f"TRX-MANUAL-{uuid.uuid4().hex[:12].upper()}"
            payment = Payment.objects.create(
                order=order,
                payment_method=Payment.Method.BANK_TRANSFER,
                amount=order.payment_amount,
                transaction_id=transaction_id,
                status=Payment.Status.PENDING
            )
        
        from payments.services import PaymentService
        pay_service = PaymentService()
        try:
            pay_service.verify_payment(
                transaction_id=payment.transaction_id,
                success=True,
                payload={'verified_by': request.user.email, 'verified_at': str(timezone.now())}
            )
            messages.success(request, f"Pesanan {order.order_number} berhasil diverifikasi Lunas!")
        except Exception as e:
            messages.error(request, f"Gagal memverifikasi pembayaran: {str(e)}")
            
        return redirect('admin_order_detail', pk=order.id)


# ==========================================
# USER MANAGEMENT (CUSTOMERS & ADMINS)
# ==========================================

class AdminUserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'dashboard/user_list.html'
    context_object_name = 'users_list'
    paginate_by = 10

    def get_queryset(self):
        # Allow searching users by name or email
        q = self.request.GET.get('q', '')
        if q:
            return User.objects.filter(Q(username__icontains=q) | Q(email__icontains=q)).order_by('-date_joined')
        return User.objects.all().order_by('-date_joined')


class AdminUserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserManageForm
    template_name = 'dashboard/user_form.html'
    success_url = reverse_lazy('admin_user_list')

    def form_valid(self, form):
        messages.success(self.request, "Status user diperbarui.")
        return super().form_valid(form)


class AdminUserDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user_to_delete = get_object_or_404(User, id=pk)
        
        if user_to_delete == request.user:
            messages.error(request, "Anda tidak dapat menghapus akun Anda sendiri.")
            return redirect('admin_user_list')
            
        if user_to_delete.role == User.Role.SUPER_ADMIN and request.user.role != User.Role.SUPER_ADMIN:
            messages.error(request, "Anda tidak memiliki wewenang untuk menghapus akun Super Admin.")
            return redirect('admin_user_list')
            
        email = user_to_delete.email
        user_to_delete.delete()
        messages.success(request, f"Akun pengguna {email} berhasil dihapus secara permanen.")
        return redirect('admin_user_list')



# ==========================================
# REPORTS & DATA EXPORT (CSV, EXCEL, PDF)
# ==========================================

class ReportsView(AdminRequiredMixin, TemplateView):
    template_name = 'dashboard/reports.html'


class ExportReportView(AdminRequiredMixin, View):
    def get(self, request):
        report_type = request.GET.get('type', 'sales') # sales, product, customer
        export_format = request.GET.get('format', 'csv') # csv, excel, pdf
        
        # Fetch report dataset based on type
        if report_type == 'sales':
            queryset = Order.objects.all().select_related('user').order_by('-created_at')
            filename = f"laporan_penjualan_{timezone.now().strftime('%Y%m%d')}"
            headers = ['Order ID', 'Pelanggan', 'Status', 'Total Belanja', 'Biaya Kirim', 'Diskon', 'Tanggal']
            data_rows = [
                [o.order_number, o.user.email, o.get_status_display(), o.total_amount, o.shipping_cost, o.discount_amount, o.created_at.strftime('%Y-%m-%d %H:%M')]
                for o in queryset
            ]
        elif report_type == 'product':
            queryset = Product.objects.all().select_related('category', 'brand').order_by('-stock')
            filename = f"laporan_produk_{timezone.now().strftime('%Y%m%d')}"
            headers = ['SKU', 'Nama Produk', 'Kategori', 'Brand', 'Harga', 'Stok', 'Status']
            data_rows = [
                [p.sku, p.name, p.category.name, p.brand.name, p.price, p.stock, 'Aktif' if p.is_active else 'Nonaktif']
                for p in queryset
            ]
        else: # customer
            queryset = User.objects.filter(role=User.Role.CUSTOMER).annotate(orders_count=Count('orders')).order_by('-orders_count')
            filename = f"laporan_pelanggan_{timezone.now().strftime('%Y%m%d')}"
            headers = ['ID', 'Username', 'Email', 'Tanggal Gabung', 'Jumlah Order', 'Status Ban']
            data_rows = [
                [u.id, u.username, u.email, u.date_joined.strftime('%Y-%m-%d'), u.orders_count, 'Banned' if u.is_banned else 'Aktif']
                for u in queryset
            ]

        # 1. Export CSV
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(data_rows)
            return response

        # 2. Export Excel
        elif export_format == 'excel':
            if not OPENPYXL_AVAILABLE:
                return HttpResponse("Modul openpyxl tidak tersedia. Pasang openpyxl untuk mengekspor ke Excel.", status=500)
                
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = report_type.capitalize()
            ws.append(headers)
            for row in data_rows:
                ws.append(row)
            
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
            wb.save(response)
            return response

        # 3. Export PDF
        elif export_format == 'pdf':
            context = {
                'title': f"Laporan {report_type.capitalize()}",
                'headers': headers,
                'rows': data_rows,
                'date': timezone.now()
            }
            # Inline CSS inside template for PDF styling
            html_string = render(request, 'dashboard/report_pdf_template.html', context).content.decode('utf-8')
            
            pdf_file = BytesIO()
            if XHTML2PDF_AVAILABLE:
                pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
                if not pisa_status.err:
                    response = HttpResponse(pdf_file.getvalue(), content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                    return response
            
            # Simple Text fallback if PDF rendering fails
            response = HttpResponse(f"Export PDF: {filename}\nHeaders: {headers}\nData: {data_rows}", content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{filename}.txt"'
            return response

        return HttpResponse("Format ekspor tidak didukung.", status=400)
