from django.db import models
from django.conf import settings

from point_of_sale.mixins import TimestampMixin
from products.models import Product


class StockMovement(TimestampMixin, models.Model):
    class MovementType(models.TextChoices):
        RECEIVED = "received", "Received"
        SOLD = "sold", "Sold"
        ADJUSTMENT = "adjustment", "Adjustment"
        RETURNED = "returned", "Returned"
        DAMAGED = "damaged", "Damaged"
        TRANSFER = "transfer", "Transfer"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField(help_text="Positive for IN, negative for OUT")
    reference = models.CharField(max_length=255, blank=True, default="", help_text="e.g. order #, invoice #, reason")
    notes = models.TextField(blank=True, default="")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="stock_movements",
    )
    running_stock = models.IntegerField(default=0, help_text="Stock level after this movement")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} | {self.get_movement_type_display()} | {self.quantity:+d}"

    @property
    def direction(self):
        return "IN" if self.quantity > 0 else "OUT"


class LowStockAlert(TimestampMixin, models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="low_stock_alerts")
    current_stock = models.IntegerField()
    threshold = models.IntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Low stock: {self.product.name} ({self.current_stock}/{self.threshold})"
