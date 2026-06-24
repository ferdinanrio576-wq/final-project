from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from orders.models import Order
from .models import Payment
from .services import PaymentService

# Info rekening per bank (static data — sesuaikan dengan rekening asli)
BANK_ACCOUNTS = {
    'BCA': {
        'name': 'Bank Central Asia (BCA)',
        'account_number': '1234567890',
        'account_name': 'PT ElectroShop Indonesia',
        'logo_text': 'BCA',
        'color': '#005bab',
    },
    'BNI': {
        'name': 'Bank Negara Indonesia (BNI)',
        'account_number': '0987654321',
        'account_name': 'PT ElectroShop Indonesia',
        'logo_text': 'BNI',
        'color': '#f26522',
    },
    'BRI': {
        'name': 'Bank Rakyat Indonesia (BRI)',
        'account_number': '1122334455',
        'account_name': 'PT ElectroShop Indonesia',
        'logo_text': 'BRI',
        'color': '#00529b',
    },
    'MANDIRI': {
        'name': 'Bank Mandiri',
        'account_number': '5544332211',
        'account_name': 'PT ElectroShop Indonesia',
        'logo_text': 'Mandiri',
        'color': '#003087',
    },
    'BSI': {
        'name': 'Bank Syariah Indonesia (BSI)',
        'account_number': '7788990011',
        'account_name': 'PT ElectroShop Indonesia',
        'logo_text': 'BSI',
        'color': '#4caf50',
    },
}

MAX_PROOF_SIZE_BYTES = 70 * 1024  # 70 KB
ALLOWED_PROOF_EXTENSIONS = ['jpg', 'jpeg', 'png']


class ProcessPaymentView(LoginRequiredMixin, View):
    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.status != Order.Status.PENDING:
            messages.warning(request, "Pesanan ini sudah dibayar atau dibatalkan.")
            return redirect('order_detail', order_number=order.order_number)

        return render(request, 'payments/payment_checkout.html', {
            'order': order,
            'bank_choices': Payment.BankChoice.choices,
            'bank_accounts': BANK_ACCOUNTS,
            'default_bank': 'BCA',
        })

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)

        if order.status != Order.Status.PENDING:
            messages.error(request, "Pesanan tidak dapat dibayar.")
            return redirect('order_detail', order_number=order.order_number)

        selected_bank = request.POST.get('selected_bank', '').strip()
        proof_file = request.FILES.get('proof_of_transfer')

        # ── Validasi bank dipilih ────────────────────────────────────────────
        valid_banks = [code for code, _ in Payment.BankChoice.choices]
        if not selected_bank or selected_bank not in valid_banks:
            messages.error(request, "Silakan pilih bank tujuan transfer terlebih dahulu.")
            return render(request, 'payments/payment_checkout.html', {
                'order': order,
                'bank_choices': Payment.BankChoice.choices,
                'bank_accounts': BANK_ACCOUNTS,
                'default_bank': selected_bank or 'BCA',
            })

        # ── Validasi bukti transfer ──────────────────────────────────────────
        if not proof_file:
            messages.error(request, "Bukti transfer wajib diunggah.")
            return render(request, 'payments/payment_checkout.html', {
                'order': order,
                'bank_choices': Payment.BankChoice.choices,
                'bank_accounts': BANK_ACCOUNTS,
                'default_bank': selected_bank,
            })

        # Cek ekstensi file
        ext = proof_file.name.rsplit('.', 1)[-1].lower() if '.' in proof_file.name else ''
        if ext not in ALLOWED_PROOF_EXTENSIONS:
            messages.error(request, "Format file tidak didukung. Harap unggah file JPG, JPEG, atau PNG.")
            return render(request, 'payments/payment_checkout.html', {
                'order': order,
                'bank_choices': Payment.BankChoice.choices,
                'bank_accounts': BANK_ACCOUNTS,
                'default_bank': selected_bank,
            })

        # Cek ukuran file (max 70 KB)
        if proof_file.size > MAX_PROOF_SIZE_BYTES:
            size_kb = proof_file.size / 1024
            messages.error(
                request,
                f"Ukuran file terlalu besar ({size_kb:.1f} KB). Maksimal ukuran file adalah 70 KB. "
                f"Silakan kompres gambar terlebih dahulu."
            )
            return render(request, 'payments/payment_checkout.html', {
                'order': order,
                'bank_choices': Payment.BankChoice.choices,
                'bank_accounts': BANK_ACCOUNTS,
                'default_bank': selected_bank,
            })

        # ── Proses pembayaran ────────────────────────────────────────────────
        pay_service = PaymentService()
        try:
            pay_service.confirm_bank_transfer(
                order=order,
                payment_method=Payment.Method.BANK_TRANSFER,
                selected_bank=selected_bank,
                proof_of_transfer=proof_file,
            )
            bank_name = dict(Payment.BankChoice.choices).get(selected_bank, selected_bank)
            messages.success(
                request,
                f"Konfirmasi pembayaran via {bank_name} berhasil dikirim. "
                f"Kami akan memverifikasi transfer sebesar Rp {order.payment_amount:,.0f} Anda."
            )
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat memproses pembayaran: {str(e)}")

        return redirect('order_detail', order_number=order.order_number)
