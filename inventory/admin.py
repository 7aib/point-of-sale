from django.contrib import admin

from .models import StockMovement, LowStockAlert


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "quantity", "running_stock", "performed_by", "created_at")
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__name", "product__sku", "reference")
    readonly_fields = ("running_stock",)


@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    list_display = ("product", "current_stock", "threshold", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("product__name", "product__sku")
