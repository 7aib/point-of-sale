from django.db import models

from config import (
    PROJECT_NAME, PROJECT_FULL_NAME, LOGO_ICON, LOGO_TEXT, SLOGAN,
    WEBSITE_URL, SUPPORT_EMAIL, PHONE_NUMBER,
    STORE_NAME, STORE_ADDRESS, STORE_CURRENCY, STORE_CURRENCY_SYMBOL, COUNTRY_CODE,
    HERO_IMAGE_URL, FAVICON,
    SOCIAL_FACEBOOK, SOCIAL_INSTAGRAM, SOCIAL_TWITTER,
    TAX_RATE, TAX_LABEL,
    RECEIPT_FOOTER_TEXT, RECEIPT_WIDTH,
    PRODUCTS_PER_PAGE, ORDERS_PER_PAGE, CUSTOMERS_PER_PAGE, DISCOUNTS_PER_PAGE,
)


class StoreSettings(models.Model):
    # Branding
    project_name = models.CharField(max_length=200, default=PROJECT_NAME)
    project_full_name = models.CharField(max_length=300, default=PROJECT_FULL_NAME)
    logo_icon = models.ImageField(upload_to="branding/", blank=True, null=True)
    logo_text = models.CharField(max_length=50, default=LOGO_TEXT)
    slogan = models.CharField(max_length=300, default=SLOGAN, blank=True)

    # Contact
    website_url = models.URLField(max_length=500, default=WEBSITE_URL, blank=True)
    support_email = models.EmailField(max_length=300, default=SUPPORT_EMAIL, blank=True)
    phone_number = models.CharField(max_length=50, default=PHONE_NUMBER, blank=True)

    # Store Info
    store_name = models.CharField(max_length=300, default=STORE_NAME)
    store_address = models.TextField(default=STORE_ADDRESS, blank=True)
    store_currency = models.CharField(max_length=10, default=STORE_CURRENCY)
    store_currency_symbol = models.CharField(max_length=10, default=STORE_CURRENCY_SYMBOL)
    country_code = models.CharField(max_length=5, default=COUNTRY_CODE)

    # Media
    hero_image_url = models.URLField(max_length=500, default=HERO_IMAGE_URL, blank=True)
    favicon = models.ImageField(upload_to="branding/", blank=True, null=True)

    # Social Links
    social_facebook = models.URLField(max_length=500, default=SOCIAL_FACEBOOK, blank=True)
    social_instagram = models.URLField(max_length=500, default=SOCIAL_INSTAGRAM, blank=True)
    social_twitter = models.URLField(max_length=500, default=SOCIAL_TWITTER, blank=True)

    # Tax Settings
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=TAX_RATE,
        help_text="Global tax rate as decimal (e.g. 0.17 for 17%)",
    )
    tax_label = models.CharField(max_length=50, default=TAX_LABEL)

    # Receipt Settings
    receipt_footer_text = models.CharField(max_length=500, default=RECEIPT_FOOTER_TEXT, blank=True)
    receipt_width = models.PositiveIntegerField(default=RECEIPT_WIDTH)

    # Pagination
    products_per_page = models.PositiveIntegerField(default=PRODUCTS_PER_PAGE)
    orders_per_page = models.PositiveIntegerField(default=ORDERS_PER_PAGE)
    customers_per_page = models.PositiveIntegerField(default=CUSTOMERS_PER_PAGE)
    discounts_per_page = models.PositiveIntegerField(default=DISCOUNTS_PER_PAGE)

    class Meta:
        verbose_name = "Store Settings"
        verbose_name_plural = "Store Settings"

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def to_dict(self):
        return {
            "PROJECT_NAME": self.project_name,
            "PROJECT_FULL_NAME": self.project_full_name,
            "LOGO_ICON": self.logo_icon.url if self.logo_icon else "",
            "LOGO_TEXT": self.logo_text,
            "SLOGAN": self.slogan,
            "WEBSITE_URL": self.website_url,
            "SUPPORT_EMAIL": self.support_email,
            "PHONE_NUMBER": self.phone_number,
            "STORE_NAME": self.store_name,
            "STORE_ADDRESS": self.store_address,
            "STORE_CURRENCY": self.store_currency,
            "STORE_CURRENCY_SYMBOL": self.store_currency_symbol,
            "COUNTRY_CODE": self.country_code,
            "HERO_IMAGE_URL": self.hero_image_url,
            "FAVICON": self.favicon.url if self.favicon else "",
            "SOCIAL_FACEBOOK": self.social_facebook,
            "SOCIAL_INSTAGRAM": self.social_instagram,
            "SOCIAL_TWITTER": self.social_twitter,
            "TAX_RATE": float(self.tax_rate),
            "TAX_LABEL": self.tax_label,
            "RECEIPT_FOOTER_TEXT": self.receipt_footer_text,
            "RECEIPT_WIDTH": self.receipt_width,
            "PRODUCTS_PER_PAGE": self.products_per_page,
            "ORDERS_PER_PAGE": self.orders_per_page,
            "CUSTOMERS_PER_PAGE": self.customers_per_page,
            "DISCOUNTS_PER_PAGE": self.discounts_per_page,
        }
