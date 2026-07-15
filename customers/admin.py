from django.contrib import admin

from .models import Customer, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price", "total_price")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "city", "created_at")
    list_filter = ("city",)
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering = ("-created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "total_amount", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("order_number", "customer__first_name", "customer__last_name")
    readonly_fields = ("order_number",)
    inlines = [OrderItemInline]
    ordering = ("-created_at",)
