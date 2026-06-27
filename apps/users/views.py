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
from .models import User, Profile, Address, EmailOTP
from .forms import LoginForm, RegisterForm, ProfileForm, AddressForm
from .services import UserService, AddressService

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIMEOUT = 300  # seconds


class RegisterView(FormView):
    template_name = 'auth/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('otp_verify')

    def form_valid(self, form):
        service = UserService()
        user = service.register_customer(
            email=form.cleaned_data['email'],
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        # Kirim OTP ke email
        try:
            service.send_otp_email(user)
            # Simpan user_id di session untuk proses verifikasi OTP
            self.request.session['otp_user_id'] = user.id
            self.request.session['otp_email'] = user.email
            messages.success(
                self.request,
                f"Registrasi berhasil! Kode verifikasi OTP telah dikirim ke {EmailOTP.mask_email(user.email)}."
            )
        except Exception as e:
            # Jika email gagal terkirim, tetap simpan ke session agar bisa kirim ulang
            self.request.session['otp_user_id'] = user.id
            self.request.session['otp_email'] = user.email
            messages.warning(
                self.request,
                "Registrasi berhasil, namun email OTP gagal dikirim. Gunakan tombol 'Kirim Ulang OTP'."
            )
        return redirect('otp_verify')

    def form_invalid(self, form):
        messages.error(self.request, "Terjadi kesalahan pada registrasi.")
        return super().form_invalid(form)


class OTPVerificationView(View):
    """Halaman input kode OTP 6 digit setelah registrasi."""

    def get(self, request):
        user_id = request.session.get('otp_user_id')
        if not user_id:
            messages.error(request, "Sesi verifikasi tidak ditemukan. Silakan daftar ulang.")
            return redirect('register')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User tidak ditemukan.")
            return redirect('register')

        if user.email_verified:
            messages.info(request, "Email Anda sudah terverifikasi. Silakan login.")
            return redirect('login')

        masked_email = EmailOTP.mask_email(user.email)
        return render(request, 'auth/otp_verify.html', {
            'masked_email': masked_email,
            'user_email': user.email,
        })

    def post(self, request):
        user_id = request.session.get('otp_user_id')
        if not user_id:
            messages.error(request, "Sesi verifikasi tidak ditemukan.")
            return redirect('register')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User tidak ditemukan.")
            return redirect('register')

        # Gabungkan 6 digit dari input terpisah atau dari satu field
        otp_parts = [
            request.POST.get('otp_1', ''),
            request.POST.get('otp_2', ''),
            request.POST.get('otp_3', ''),
            request.POST.get('otp_4', ''),
            request.POST.get('otp_5', ''),
            request.POST.get('otp_6', ''),
        ]
        # Fallback: coba ambil dari field tunggal 'otp_code'
        otp_code = ''.join(otp_parts).strip()
        if not otp_code or len(otp_code) < 6:
            otp_code = request.POST.get('otp_code', '').strip()

        service = UserService()
        success, message = service.verify_otp(user, otp_code)

        if success:
            # Hapus session OTP
            request.session.pop('otp_user_id', None)
            request.session.pop('otp_email', None)
            messages.success(request, "Email berhasil diverifikasi! Silakan login.")
            return redirect('login')
        else:
            masked_email = EmailOTP.mask_email(user.email)
            messages.error(request, message)
            return render(request, 'auth/otp_verify.html', {
                'masked_email': masked_email,
                'user_email': user.email,
            })


class ResendOTPView(View):
    """Kirim ulang OTP ke email user."""

    def post(self, request):
        user_id = request.session.get('otp_user_id')
        if not user_id:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Sesi tidak ditemukan.'})
            messages.error(request, "Sesi verifikasi tidak ditemukan.")
            return redirect('register')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'User tidak ditemukan.'})
            return redirect('register')

        service = UserService()
        try:
            service.send_otp_email(user)
            masked_email = EmailOTP.mask_email(user.email)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'OTP baru telah dikirim ke {masked_email}.'
                })
            messages.success(request, f"OTP baru telah dikirim ke {masked_email}.")
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Gagal mengirim OTP. Coba lagi.'})
            messages.error(request, "Gagal mengirim OTP. Silakan coba lagi.")

        return redirect('otp_verify')


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
    """Verifikasi via link token (metode lama - backward compat)."""
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
