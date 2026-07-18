from django import forms

from .models import StoreSettings


class StoreSettingsForm(forms.ModelForm):
    class Meta:
        model = StoreSettings
        fields = [
            "project_name", "project_full_name", "logo_icon", "logo_text", "slogan",
            "website_url", "support_email", "phone_number",
            "store_name", "store_address", "store_currency", "store_currency_symbol", "country_code",
            "hero_image_url", "favicon",
            "social_facebook", "social_instagram", "social_twitter",
            "tax_rate", "tax_label",
            "receipt_footer_text", "receipt_width",
            "products_per_page", "orders_per_page", "customers_per_page", "discounts_per_page",
        ]
        widgets = {
            "project_name": forms.TextInput(attrs={"class": "apple-form-input"}),
            "project_full_name": forms.TextInput(attrs={"class": "apple-form-input"}),
            "logo_icon": forms.ClearableFileInput(attrs={"class": "apple-form-input", "accept": "image/*"}),
            "logo_text": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "Short brand name"}),
            "slogan": forms.TextInput(attrs={"class": "apple-form-input"}),
            "website_url": forms.URLInput(attrs={"class": "apple-form-input"}),
            "support_email": forms.EmailInput(attrs={"class": "apple-form-input"}),
            "phone_number": forms.TextInput(attrs={"class": "apple-form-input"}),
            "store_name": forms.TextInput(attrs={"class": "apple-form-input"}),
            "store_address": forms.Textarea(attrs={"class": "apple-form-input", "rows": 2}),
            "store_currency": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "e.g. PKR"}),
            "store_currency_symbol": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "e.g. Rs"}),
            "country_code": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "e.g. PK"}),
            "hero_image_url": forms.URLInput(attrs={"class": "apple-form-input"}),
            "favicon": forms.ClearableFileInput(attrs={"class": "apple-form-input", "accept": "image/*"}),
            "social_facebook": forms.URLInput(attrs={"class": "apple-form-input"}),
            "social_instagram": forms.URLInput(attrs={"class": "apple-form-input"}),
            "social_twitter": forms.URLInput(attrs={"class": "apple-form-input"}),
            "tax_rate": forms.NumberInput(attrs={"class": "apple-form-input", "step": "0.0001", "min": "0"}),
            "tax_label": forms.TextInput(attrs={"class": "apple-form-input", "placeholder": "e.g. GST"}),
            "receipt_footer_text": forms.TextInput(attrs={"class": "apple-form-input"}),
            "receipt_width": forms.NumberInput(attrs={"class": "apple-form-input", "min": "40", "max": "120"}),
            "products_per_page": forms.NumberInput(attrs={"class": "apple-form-input", "min": "5", "max": "100"}),
            "orders_per_page": forms.NumberInput(attrs={"class": "apple-form-input", "min": "5", "max": "100"}),
            "customers_per_page": forms.NumberInput(attrs={"class": "apple-form-input", "min": "5", "max": "100"}),
            "discounts_per_page": forms.NumberInput(attrs={"class": "apple-form-input", "min": "5", "max": "100"}),
        }
