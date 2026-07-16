from django.db import models
from django.conf import settings

from point_of_sale.mixins import TimestampMixin


class Payment(TimestampMixin, models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CREDIT = "credit", "Credit"
        OTHER = "other", "Other"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        "customers.Order",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.COMPLETED)
    transaction_id = models.CharField(max_length=255, blank=True, default="",
                                       help_text="External transaction reference")
    notes = models.TextField(blank=True, default="")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="payments",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.pk} - {self.amount} for {self.order.order_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update order payment status
        self.order.refresh_from_db()
        total_paid = self.order.payments.filter(
            status=self.PaymentStatus.COMPLETED
        ).aggregate(total=models.Sum("amount"))["total"] or 0
        if total_paid >= self.order.total_amount:
            self.order.status = "completed"
            self.order.save(update_fields=["status"])
        elif total_paid > 0:
            self.order.status = "pending"
            self.order.save(update_fields=["status"])
