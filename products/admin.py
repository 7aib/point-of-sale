from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "sku", "category", "cost_price", "selling_price",
        "stock_quantity", "is_active",
    )
    list_filter = ("is_active", "category")
    search_fields = ("name", "sku", "barcode")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("-created_at",)
