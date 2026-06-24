import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from products.models import Product

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True, help_text="For guest shopping cart")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.email}"
        return f"Guest Cart ({self.session_key})"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.product.final_price * self.quantity


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, related_name='wishlists', blank=True)

    def __str__(self):
        return f"Wishlist of {self.user.email}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Menunggu Pembayaran'
        AWAITING_VERIFICATION = 'AWAITING_VERIFICATION', 'Menunggu Verifikasi'
        PAID = 'PAID', 'Lunas'
        PROCESSING = 'PROCESSING', 'Diproses'
        SHIPPED = 'SHIPPED', 'Dikirim'
        COMPLETED = 'COMPLETED', 'Selesai'
        CANCELLED = 'CANCELLED', 'Dibatalkan'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Unique payment code fields
    unique_code = models.IntegerField(default=0)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, default='UNPAID')
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Store shipping address snapshot in case address is updated/deleted
    shipping_address_label = models.CharField(max_length=50, default='Rumah')
    shipping_recipient_name = models.CharField(max_length=100)
    shipping_phone_number = models.CharField(max_length=15)
    shipping_street_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_province = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=10)
    
    # Snapshot layanan pengiriman
    shipping_service = models.CharField(max_length=20, blank=True, default='REG', help_text="Paket layanan kurir: REG, YES, OKE, dll")
    
    coupon = models.ForeignKey('coupons.Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.user.email} ({self.status})"

    @property
    def final_amount(self):
        return (self.total_amount + self.shipping_cost + self.tax_amount) - self.discount_amount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} inside {self.order.order_number}"

    @property
    def subtotal(self):
        return self.price * self.quantity


class Shipment(models.Model):
    class Courier(models.TextChoices):
        JNE = 'JNE', 'Jalan Nugraha Ekakurir (JNE)'
        TIKI = 'TIKI', 'Titipan Kilat (TIKI)'
        POS = 'POS', 'POS Indonesia (POS)'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Menunggu Dikirim'
        SHIPPED = 'SHIPPED', 'Sedang Dikirim'
        DELIVERED = 'DELIVERED', 'Sudah Sampai'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipment')
    courier = models.CharField(max_length=10, choices=Courier.choices, default=Courier.JNE)
    service = models.CharField(max_length=20, blank=True, default='REG', help_text="Paket layanan: REG, YES, OKE, ONS, ECO, BIASA, KILAT")
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status in [self.Status.SHIPPED, self.Status.DELIVERED] and not self.tracking_number:
            self.tracking_number = f"TRK-{self.order.order_number.split('-')[-1]}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Shipment for {self.order.order_number} via {self.courier}"
