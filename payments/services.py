import datetime
from io import BytesIO
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from .repositories import PaymentRepository, InvoiceRepository
from .models import Payment, Invoice
from orders.models import Order
from django.db import transaction

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False


class PaymentService:
    def __init__(self):
        self.payment_repo = PaymentRepository()

    @transaction.atomic
    def confirm_bank_transfer(
        self, order: Order,
        payment_method: str,
        selected_bank: str = None,
        proof_of_transfer=None
    ) -> Payment:
        import uuid
        transaction_id = f"TRX-BT-{uuid.uuid4().hex[:12].upper()}"

        payment = self.payment_repo.create_payment(
            order=order,
            payment_method=payment_method,
            amount=order.payment_amount,
            transaction_id=transaction_id,
            selected_bank=selected_bank,
            proof_of_transfer=proof_of_transfer,
        )

        order.status = Order.Status.AWAITING_VERIFICATION
        order.payment_status = 'AWAITING_VERIFICATION'
        order.save()

        from notifications.services import NotificationService
        notif_service = NotificationService()
        bank_name = dict(Payment.BankChoice.choices).get(selected_bank, 'Bank') if selected_bank else 'Bank'
        notif_service.create_notification(
            user=order.user,
            title="Konfirmasi Pembayaran Diterima",
            message=(
                f"Konfirmasi transfer via {bank_name} untuk order {order.order_number} "
                f"telah diterima. Kami sedang memverifikasi pembayaran Anda."
            ),
            notif_type="PAYMENT"
        )

        return payment

    @transaction.atomic
    def verify_payment(self, transaction_id: str, success: bool, payload: dict = None) -> Payment:
        payment = self.payment_repo.get_by_transaction_id(transaction_id)
        if not payment:
            raise ValueError("Transaksi tidak ditemukan.")

        if success:
            payment.status = Payment.Status.SUCCESS
            payment.payment_date = datetime.datetime.now()
            payment.response_payload = payload
            payment.save()

            order = payment.order
            order.status = Order.Status.PAID
            order.paid_at = datetime.datetime.now()
            order.payment_status = 'PAID'
            order.save()

            invoice_service = InvoiceService()
            invoice_service.generate_invoice_pdf(order)

            from notifications.services import NotificationService
            notif_service = NotificationService()
            notif_service.create_notification(
                user=order.user,
                title="Pembayaran Sukses",
                message=f"Pembayaran untuk order {order.order_number} berhasil diverifikasi. Invoice Anda telah diterbitkan.",
                notif_type="PAYMENT"
            )
        else:
            payment.status = Payment.Status.FAILED
            payment.response_payload = payload
            payment.save()

            order = payment.order
            order.status = Order.Status.PENDING
            order.payment_status = 'FAILED'
            order.save()

        return payment


class InvoiceService:
    def __init__(self):
        self.invoice_repo = InvoiceRepository()

    def generate_invoice_pdf(self, order: Order) -> Invoice:
        invoice, created = self.invoice_repo.get_or_create_for_order(order)

        context = {
            'order': order,
            'invoice': invoice,
            'items': order.items.all(),
            'date': datetime.datetime.now()
        }

        html_string = render_to_string('orders/invoice_template.html', context)

        pdf_file = BytesIO()
        if XHTML2PDF_AVAILABLE:
            pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
            if not pisa_status.err:
                pdf_content = pdf_file.getvalue()
                filename = f"invoice_{order.order_number}.pdf"
                invoice.pdf_file.save(filename, ContentFile(pdf_content), save=True)
                return invoice

        mock_pdf_content = (
            f"--- INVOICE MOCK ---\n"
            f"Invoice Number: {invoice.invoice_number}\n"
            f"Order Number: {order.order_number}\n"
            f"Total Amount: Rp {order.final_amount}\n"
        )
        filename = f"invoice_{order.order_number}.pdf"
        invoice.pdf_file.save(filename, ContentFile(mock_pdf_content.encode('utf-8')), save=True)
        return invoice
