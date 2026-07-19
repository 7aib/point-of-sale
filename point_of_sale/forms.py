from django import forms
from django.utils.safestring import mark_safe

from .models import StoreSettings


class AppleFileInput(forms.ClearableFileInput):
    """Renders only the file input, no 'Currently/Clear/Change:' text."""

    def __init__(self, attrs=None):
        default_attrs = {"class": "apple-file-input", "accept": "image/*"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        return super().render(name, value, attrs=attrs, renderer=renderer)

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"].pop("initial_text", None)
        ctx["widget"].pop("input_text", None)
        ctx["widget"].pop("clear_checkbox_label", None)
        ctx["widget"].pop("checkbox_name", None)
        ctx["widget"].pop("checkbox_id", None)
        ctx["widget"].pop("is_initial", None)
        return ctx


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
            "project_name": forms.TextInput(attrs={"class": "form-control"}),
            "project_full_name": forms.TextInput(attrs={"class": "form-control"}),
            "logo_icon": AppleFileInput(),
            "logo_text": forms.TextInput(attrs={"class": "form-control", "placeholder": "Short brand name"}),
            "slogan": forms.TextInput(attrs={"class": "form-control"}),
            "website_url": forms.URLInput(attrs={"class": "form-control"}),
            "support_email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "store_name": forms.TextInput(attrs={"class": "form-control"}),
            "store_address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "store_currency": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. PKR"}),
            "store_currency_symbol": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Rs"}),
            "country_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. PK"}),
            "hero_image_url": forms.URLInput(attrs={"class": "form-control"}),
            "favicon": AppleFileInput(),
            "social_facebook": forms.URLInput(attrs={"class": "form-control"}),
            "social_instagram": forms.URLInput(attrs={"class": "form-control"}),
            "social_twitter": forms.URLInput(attrs={"class": "form-control"}),
            "tax_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "tax_label": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. GST"}),
            "receipt_footer_text": forms.TextInput(attrs={"class": "form-control"}),
            "receipt_width": forms.NumberInput(attrs={"class": "form-control", "min": "40", "max": "120"}),
            "products_per_page": forms.NumberInput(attrs={"class": "form-control", "min": "5", "max": "100"}),
            "orders_per_page": forms.NumberInput(attrs={"class": "form-control", "min": "5", "max": "100"}),
            "customers_per_page": forms.NumberInput(attrs={"class": "form-control", "min": "5", "max": "100"}),
            "discounts_per_page": forms.NumberInput(attrs={"class": "form-control", "min": "5", "max": "100"}),
        }
        help_texts = {
            "logo_icon": "Store logo used in sidebar and auth pages. Recommended: 256x256 px, PNG with transparent background. Keep under 100KB.",
            "favicon": "Browser tab icon. Recommended: 32x32 or 64x64 px, PNG/ICO format. Keep under 10KB.",
            "hero_image_url": "Background image for login/landing page. Recommended: 1920x1080 px, JPG/PNG. Keep under 500KB.",
            "logo_text": "Short brand name shown next to logo in sidebar and on auth pages.",
            "tax_rate": "Global tax rate in % (e.g. 17 for 17%). Can be overridden per product.",
            "receipt_width": "Receipt paper width in characters (standard: 80).",
        }
