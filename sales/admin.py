from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("pk", "order", "amount", "payment_method", "status", "transaction_id", "received_by", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("order__order_number", "transaction_id", "order__customer__first_name", "order__customer__last_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
