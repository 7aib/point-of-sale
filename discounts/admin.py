from django.contrib import admin

from .models import Discount, Coupon


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "discount_type", "value", "min_purchase_amount", "is_active", "usage_limit", "used_count", "valid_from", "valid_to")
    list_filter = ("discount_type", "is_active")
    search_fields = ("name", "code")
    readonly_fields = ("used_count", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "max_uses", "used_count", "max_uses_per_user", "is_active", "valid_from", "valid_to")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code", "description")
    readonly_fields = ("used_count", "created_at", "updated_at")
    ordering = ("-created_at",)
