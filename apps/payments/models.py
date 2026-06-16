import datetime
from django.db import models
from django.conf import settings
from orders.models import Order

class Payment(models.Model):
    class Method(models.TextChoices):
        MIDTRANS = 'MIDTRANS', 'Midtrans Payment Gateway'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Manual Bank Transfer'
        QRIS = 'QRIS', 'QRIS'
        E_WALLET = 'E_WALLET', 'GoPay/OVO/Dana'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Menunggu Pembayaran'
        SUCCESS = 'SUCCESS', 'Berhasil'
        FAILED = 'FAILED', 'Gagal'
        REFUNDED = 'REFUNDED', 'Dikembalikan (Refund)'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    payment_method = models.CharField(max_length=20, choices=Method.choices, default=Method.MIDTRANS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(blank=True, null=True)
    response_payload = models.JSONField(blank=True, null=True, help_text="Payload response from payment gateway")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for {self.order.order_number} - {self.amount} ({self.status})"


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    pdf_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            now = datetime.datetime.now()
            self.invoice_number = f"INV/{now.year}/{now.strftime('%m')}/{self.order.order_number.split('-')[-1]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number
