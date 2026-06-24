from django import forms
from django.contrib.auth import get_user_model
from products.models import Product, Category, Brand, ProductImage
from coupons.models import Coupon
from orders.models import Order, Shipment

User = get_user_model()

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'description', 'price', 'discount_price', 'stock', 'weight_grams', 'category', 'brand', 'is_active', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'weight_grams': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image', 'parent_category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'parent_category': forms.Select(attrs={'class': 'form-select'}),
        }


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'description', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_percentage', 'max_discount_amount', 'min_spend', 'expiry_date', 'active_limit', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contoh: DISKON10'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_discount_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_spend': forms.NumberInput(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'active_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class OrderUpdateForm(forms.ModelForm):
    tracking_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    shipment_status = forms.ChoiceField(choices=Shipment.Status.choices, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class UserManageForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role', 'is_banned']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_banned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
