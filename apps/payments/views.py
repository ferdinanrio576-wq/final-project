from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from orders.models import Order
from .models import Payment
from .services import PaymentService

class ProcessPaymentView(LoginRequiredMixin, View):
    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.status != Order.Status.PENDING:
            messages.warning(request, "Pesanan ini sudah dibayar atau dibatalkan.")
            return redirect('order_detail', order_number=order.order_number)

        payment_methods = Payment.Method.choices
        return render(request, 'payments/payment_checkout.html', {
            'order': order,
            'payment_methods': payment_methods
        })

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        payment_method = request.POST.get('payment_method', Payment.Method.BANK_TRANSFER)

        if order.status != Order.Status.PENDING:
            messages.error(request, "Pesanan tidak dapat dibayar.")
            return redirect('order_detail', order_number=order.order_number)

        pay_service = PaymentService()
        try:
            # Confirm bank transfer
            pay_service.confirm_bank_transfer(order, payment_method)
            messages.success(request, f"Konfirmasi pembayaran berhasil dikirim. Kami akan memverifikasi transfer sebesar Rp {order.payment_amount:,.0f} Anda.")
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat memproses pembayaran: {str(e)}")

        return redirect('order_detail', order_number=order.order_number)
