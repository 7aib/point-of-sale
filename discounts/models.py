from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from point_of_sale.mixins import TimestampMixin, ActiveMixin


class Discount(TimestampMixin, ActiveMixin, models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, db_index=True,
                            help_text="Unique discount code (e.g. SUMMER20)")
    description = models.TextField(blank=True, default="")
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    value = models.DecimalField(max_digits=10, decimal_places=2,
                                help_text="Percentage (e.g. 20) or fixed amount in store currency")
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                              help_text="Minimum order amount to apply discount (0 = no minimum)")
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                              help_text="Maximum discount cap for percentage type (0 = no cap)")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True,
                                    help_text="Leave blank for no expiry")
    usage_limit = models.PositiveIntegerField(default=0,
                                              help_text="Maximum number of times this discount can be used (0 = unlimited)")
    used_count = models.PositiveIntegerField(default=0)
    applies_to_products = models.ManyToManyField("products.Product", blank=True, related_name="discounts")
    applies_to_categories = models.ManyToManyField("products.Category", blank=True, related_name="discounts")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_display_value()})"

    def clean(self):
        if self.discount_type == self.DiscountType.PERCENTAGE and self.value > 100:
            raise ValidationError({"value": "Percentage cannot exceed 100%."})
        if self.value <= 0:
            raise ValidationError({"value": "Discount value must be greater than 0."})
        if self.valid_to and self.valid_from and self.valid_to <= self.valid_from:
            raise ValidationError({"valid_to": "End date must be after start date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.usage_limit > 0 and self.used_count >= self.usage_limit:
            return False
        return True

    @property
    def is_expired(self):
        if not self.valid_to:
            return False
        return timezone.now() > self.valid_to

    @property
    def usage_remaining(self):
        if self.usage_limit == 0:
            return None
        return max(0, self.usage_limit - self.used_count)

    def get_display_value(self):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return f"{self.value}%"
        from django.conf import settings
        from config import STORE_CURRENCY_SYMBOL
        return f"{STORE_CURRENCY_SYMBOL} {self.value}"

    def calculate_discount(self, subtotal):
        if not self.is_valid:
            return 0
        if self.min_purchase_amount > 0 and subtotal < self.min_purchase_amount:
            return 0
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = subtotal * (self.value / 100)
            if self.max_discount_amount > 0:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.value, subtotal)
        return round(discount, 2)


class Coupon(TimestampMixin, ActiveMixin, models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")
    discount_type = models.CharField(max_length=20,
                                     choices=Discount.DiscountType.choices,
                                     default=Discount.DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_uses = models.PositiveIntegerField(default=0,
                                           help_text="Total times this coupon can be redeemed (0 = unlimited)")
    used_count = models.PositiveIntegerField(default=0)
    max_uses_per_user = models.PositiveIntegerField(default=1,
                                                    help_text="Max times a single user can use this coupon")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True,
                                    help_text="Leave blank for no expiry")
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           help_text="Minimum order amount required (0 = no minimum)")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.get_display_value()}"

    def clean(self):
        if self.discount_type == Discount.DiscountType.PERCENTAGE and self.discount_value > 100:
            raise ValidationError({"discount_value": "Percentage cannot exceed 100%."})
        if self.discount_value <= 0:
            raise ValidationError({"discount_value": "Discount value must be greater than 0."})
        if self.valid_to and self.valid_from and self.valid_to <= self.valid_from:
            raise ValidationError({"valid_to": "End date must be after start date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        return True

    @property
    def is_expired(self):
        if not self.valid_to:
            return False
        return timezone.now() > self.valid_to

    @property
    def usage_remaining(self):
        if self.max_uses == 0:
            return None
        return max(0, self.max_uses - self.used_count)

    def get_display_value(self):
        if self.discount_type == Discount.DiscountType.PERCENTAGE:
            return f"{self.discount_value}% off"
        from config import STORE_CURRENCY_SYMBOL
        return f"{STORE_CURRENCY_SYMBOL} {self.discount_value} off"

    def calculate_discount(self, subtotal):
        if not self.is_valid:
            return 0
        if self.min_order_amount > 0 and subtotal < self.min_order_amount:
            return 0
        if self.discount_type == Discount.DiscountType.PERCENTAGE:
            return round(subtotal * (self.discount_value / 100), 2)
        else:
            return round(min(self.discount_value, subtotal), 2)

    def redeem(self):
        self.used_count += 1
        self.save(update_fields=["used_count"])
