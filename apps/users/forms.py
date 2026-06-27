from django import forms
from django.contrib.auth import get_user_model
from .models import Profile, Address

User = get_user_model()

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'nama@email.com', 'id': 'login-email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Kata Sandi', 'id': 'login-password'
    }))


class RegisterForm(forms.ModelForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Username', 'id': 'reg-username'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'nama@email.com', 'id': 'reg-email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Kata Sandi minimal 6 karakter', 'id': 'reg-password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Konfirmasi Kata Sandi', 'id': 'reg-confirm-password'
    }))

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email sudah terdaftar.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Kata sandi tidak cocok.")
        return cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'birth_date', 'gender', 'avatar']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: 08123456789'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'label', 'recipient_name', 'phone_number', 'street_address',
            'city', 'province', 'postal_code', 'place_id', 'latitude', 'longitude', 'is_default'
        ]
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: Rumah, Kantor'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama Penerima'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nomor Telepon'}),
            'street_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alamat Lengkap'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kota/Kabupaten'}),
            'province': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Provinsi'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kode Pos'}),
            'place_id': forms.HiddenInput(),
            'latitude': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: -7.424494', 'id': 'id_latitude'}),
            'longitude': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: 109.230154', 'id': 'id_longitude'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        place_id = cleaned.get('place_id')
        latitude = cleaned.get('latitude')
        longitude = cleaned.get('longitude')

        # If a place_id is provided (from Google Maps), ensure lat/lng exist
        if place_id:
            if latitude in (None, '') or longitude in (None, ''):
                self.add_error('place_id', 'Jika menggunakan pemilihan alamat, koordinat (latitude/longitude) harus tersedia.')
                raise forms.ValidationError('Koordinat alamat tidak lengkap untuk Place ID.')

        return cleaned
