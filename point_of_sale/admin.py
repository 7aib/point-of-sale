from django.contrib import admin

from .models import StoreSettings


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Branding", {
            "fields": ("project_name", "project_full_name", "logo_icon", "logo_text", "slogan"),
        }),
        ("Contact", {
            "fields": ("website_url", "support_email", "phone_number"),
        }),
        ("Store Info", {
            "fields": ("store_name", "store_address", "store_currency", "store_currency_symbol", "country_code"),
        }),
        ("Media", {
            "fields": ("hero_image_url", "favicon"),
        }),
        ("Social Links", {
            "fields": ("social_facebook", "social_instagram", "social_twitter"),
        }),
        ("Tax Settings", {
            "fields": ("tax_rate", "tax_label"),
        }),
        ("Receipt Settings", {
            "fields": ("receipt_footer_text", "receipt_width"),
        }),
        ("Pagination", {
            "fields": ("products_per_page", "orders_per_page", "customers_per_page", "discounts_per_page"),
        }),
    )
    list_display = ("store_name", "store_currency", "tax_label")
    list_display_links = ("store_name",)

    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
