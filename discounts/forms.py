from django import forms
from django.utils import timezone

from .models import Discount, Coupon


class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = [
            "name", "code", "description", "discount_type", "value",
            "min_purchase_amount", "max_discount_amount",
            "valid_from", "valid_to", "usage_limit",
            "is_active", "applies_to_products", "applies_to_categories",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "Discount name"}),
            "code": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "e.g. SUMMER20", "style": "text-transform: uppercase;"}),
            "description": forms.Textarea(attrs={"class": "apple-form-input", "rows": 3, "placeholder": "Description (optional)"}),
            "discount_type": forms.Select(attrs={"class": "apple-form-select"}),
            "value": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "e.g. 20", "step": "0.01"}),
            "min_purchase_amount": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "0 for no minimum", "step": "0.01"}),
            "max_discount_amount": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "0 for no cap", "step": "0.01"}),
            "valid_from": forms.DateTimeInput(attrs={"class": "apple-form-input", "type": "datetime-local"}),
            "valid_to": forms.DateTimeInput(attrs={"class": "apple-form-input", "type": "datetime-local"}),
            "usage_limit": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "0 for unlimited"}),
            "is_active": forms.CheckboxInput(attrs={"class": "apple-form-checkbox"}),
            "applies_to_products": forms.SelectMultiple(attrs={"class": "apple-form-select", "size": "8"}),
            "applies_to_categories": forms.SelectMultiple(attrs={"class": "apple-form-select", "size": "5"}),
        }

    def clean_code(self):
        code = self.cleaned_data.get("code", "").upper().strip()
        if code:
            qs = Discount.objects.filter(code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A discount with this code already exists.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get("discount_type")
        value = cleaned_data.get("value")
        if discount_type == Discount.DiscountType.PERCENTAGE and value and value > 100:
            self.add_error("value", "Percentage cannot exceed 100%.")
        return cleaned_data


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            "code", "description", "discount_type", "discount_value",
            "max_uses", "max_uses_per_user", "min_order_amount",
            "valid_from", "valid_to", "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "e.g. SAVE10", "style": "text-transform: uppercase;"}),
            "description": forms.Textarea(attrs={"class": "apple-form-input", "rows": 3, "placeholder": "Description (optional)"}),
            "discount_type": forms.Select(attrs={"class": "apple-form-select"}),
            "discount_value": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "e.g. 10", "step": "0.01"}),
            "max_uses": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "0 for unlimited"}),
            "max_uses_per_user": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "1"}),
            "min_order_amount": forms.NumberInput(attrs={"class": "apple-form-input", "placeholder": "0 for no minimum", "step": "0.01"}),
            "valid_from": forms.DateTimeInput(attrs={"class": "apple-form-input", "type": "datetime-local"}),
            "valid_to": forms.DateTimeInput(attrs={"class": "apple-form-input", "type": "datetime-local"}),
            "is_active": forms.CheckboxInput(attrs={"class": "apple-form-checkbox"}),
        }

    def clean_code(self):
        code = self.cleaned_data.get("code", "").upper().strip()
        if code:
            qs = Coupon.objects.filter(code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A coupon with this code already exists.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        discount_type = cleaned_data.get("discount_type")
        discount_value = cleaned_data.get("discount_value")
        if discount_type == Discount.DiscountType.PERCENTAGE and discount_value and discount_value > 100:
            self.add_error("discount_value", "Percentage cannot exceed 100%.")
        return cleaned_data
