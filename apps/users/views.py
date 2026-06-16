from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.views.generic import FormView, TemplateView, CreateView, UpdateView, DeleteView
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.cache import cache
from .models import User, Profile, Address
from .forms import LoginForm, RegisterForm, ProfileForm, AddressForm
from .services import UserService, AddressService

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIMEOUT = 300  # seconds

class RegisterView(FormView):
    template_name = 'auth/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        service = UserService()
        user = service.register_customer(
            email=form.cleaned_data['email'],
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        try:
            service.send_verification_email(user, self.request)
            messages.success(self.request, "Registrasi sukses! Cek email Anda untuk verifikasi akun.")
        except Exception:
            messages.success(self.request, "Registrasi sukses! Silakan login, namun verifikasi email gagal dikirim.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Terjadi kesalahan pada registrasi.")
        return super().form_invalid(form)


class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        cache_key = f'login_attempts_{email}'
        attempts = cache.get(cache_key, 0)

        if attempts >= MAX_LOGIN_ATTEMPTS:
            messages.error(self.request, "Terlalu banyak percobaan login. Silakan coba lagi beberapa menit lagi.")
            return self.form_invalid(form)

        user = authenticate(self.request, username=email, password=password)
        
        if user is not None:
            if user.is_banned:
                messages.error(self.request, "Akun Anda ditangguhkan (banned).")
                return self.form_invalid(form)
            login(self.request, user)
            cache.delete(cache_key)
            messages.success(self.request, f"Selamat datang kembali, {user.username}!")
            
            # Redirect admin to dashboard
            if user.is_admin_user:
                return redirect('dashboard_index')
                
            return super().form_valid(form)

        attempts += 1
        cache.set(cache_key, attempts, LOGIN_LOCKOUT_TIMEOUT)
        remaining = MAX_LOGIN_ATTEMPTS - attempts
        messages.error(self.request, f"Email atau Kata Sandi salah. Sisa percobaan: {remaining}.")
        return self.form_invalid(form)


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Anda berhasil keluar.")
        return redirect('product_list')


class EmailVerificationView(View):
    def get(self, request, uidb64, token):
        service = UserService()
        success = service.verify_email(uidb64, token)
        if success:
            messages.success(request, "Email berhasil diverifikasi. Anda dapat masuk sekarang.")
            return redirect('login')
        messages.error(request, "Tautan verifikasi email tidak valid atau sudah kadaluarsa.")
        return redirect('register')


class ResendVerificationEmailView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'auth/verification_email_sent.html')

    def post(self, request):
        service = UserService()
        try:
            service.send_verification_email(request.user, request)
            messages.success(request, "Email verifikasi baru telah dikirim.")
        except Exception:
            messages.error(request, "Gagal mengirim email verifikasi. Coba lagi nanti.")
        return redirect('profile')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'auth/password_reset_form.html'
    email_template_name = 'auth/password_reset_email.txt'
    subject_template_name = 'auth/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'auth/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'auth/password_reset_complete.html'


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'auth/password_change_form.html'
    success_url = reverse_lazy('password_change_done')


class CustomPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'auth/password_change_done.html'


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        profile_form = ProfileForm(instance=profile)
        return render(request, 'auth/profile.html', {
            'profile_form': profile_form,
            'profile': profile
        })

    def post(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profil berhasil diperbarui.")
            return redirect('profile')
        messages.error(request, "Terjadi kesalahan saat memperbarui profil.")
        return render(request, 'auth/profile.html', {
            'profile_form': profile_form,
            'profile': profile
        })


class AddressListView(LoginRequiredMixin, TemplateView):
    template_name = 'auth/address_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['addresses'] = Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')
        return context


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = 'auth/address_form.html'
    success_url = reverse_lazy('address_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            return JsonResponse({
                'success': True,
                'message': "Alamat berhasil ditambahkan.",
                'address': {
                    'id': self.object.id,
                    'label': self.object.label,
                    'recipient_name': self.object.recipient_name,
                    'phone_number': self.object.phone_number,
                    'street_address': self.object.street_address,
                    'city': self.object.city,
                    'province': self.object.province,
                    'postal_code': self.object.postal_code,
                }
            })
        messages.success(self.request, "Alamat berhasil ditambahkan.")
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            return JsonResponse({
                'success': False,
                'errors': form.errors.get_json_data()
            }, status=400)
        return super().form_invalid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'auth/address_form.html'
    success_url = reverse_lazy('address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Alamat berhasil diperbarui.")
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    model = Address
    success_url = reverse_lazy('address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Alamat berhasil dihapus.")
        return super().delete(request, *args, **kwargs)
