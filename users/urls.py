from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, ProfileView,
    AddressListView, AddressCreateView, AddressUpdateView, AddressDeleteView,
    OTPVerificationView, ResendOTPView,
    EmailVerificationView, ResendVerificationEmailView,
    CustomPasswordResetView, CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView, CustomPasswordResetCompleteView,
    CustomPasswordChangeView, CustomPasswordChangeDoneView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-email/<uidb64>/<token>/', EmailVerificationView.as_view(), name='verify_email'),
    path('verify-email/resend/', ResendVerificationEmailView.as_view(), name='resend_verification_email'),
    path('otp/verify/', OTPVerificationView.as_view(), name='otp_verify'),
    path('otp/resend/', ResendOTPView.as_view(), name='resend_otp'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', CustomPasswordChangeDoneView.as_view(), name='password_change_done'),
    
    path('addresses/', AddressListView.as_view(), name='address_list'),
    path('addresses/add/', AddressCreateView.as_view(), name='address_add'),
    path('addresses/<int:pk>/edit/', AddressUpdateView.as_view(), name='address_edit'),
    path('addresses/<int:pk>/delete/', AddressDeleteView.as_view(), name='address_delete'),
]
