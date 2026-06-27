from .models import Payment, Invoice
from orders.models import Order
from typing import Optional, Tuple


class PaymentRepository:
    @staticmethod
    def get_by_transaction_id(transaction_id: str) -> Optional[Payment]:
        try:
            return Payment.objects.select_related('order').get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return None

    @staticmethod
    def get_by_order(order: Order) -> Optional[Payment]:
        return Payment.objects.filter(order=order).order_by('-created_at').first()

    @staticmethod
    def create_payment(
        order: Order,
        payment_method: str,
        amount: float,
        transaction_id: str = None,
        selected_bank: str = None,
        proof_of_transfer=None
    ) -> Payment:
        return Payment.objects.create(
            order=order,
            payment_method=payment_method,
            amount=amount,
            transaction_id=transaction_id,
            status=Payment.Status.PENDING,
            selected_bank=selected_bank,
            proof_of_transfer=proof_of_transfer,
        )


class InvoiceRepository:
    @staticmethod
    def get_or_create_for_order(order: Order) -> Tuple[Invoice, bool]:
        return Invoice.objects.get_or_create(order=order)
