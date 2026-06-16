from django.urls import path
from .views import ProcessPaymentView

urlpatterns = [
    path('checkout/<str:order_number>/', ProcessPaymentView.as_view(), name='process_payment'),
]
