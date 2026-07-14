from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone

from point_of_sale.mixins import TimestampMixin


class UserRoles(models.TextChoices):
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    CASHIER = "cashier", "Cashier"
    CUSTOMER = "customer", "Customer"


class SoftDeleteUserManager(UserManager):
    """UserManager with soft delete: skips deleted users by default."""
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def hard_deleted(self):
        return super().get_queryset().filter(is_deleted=True)

    def all_with_deleted(self):
        return super().get_queryset()


class User(TimestampMixin, AbstractUser):
    role = models.CharField(max_length=20, choices=UserRoles.choices, default=UserRoles.CASHIER)
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        help_text="Format: +92XXXXXXXXXX (e.g. +9230112345678)",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteUserManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])

    @property
    def is_admin(self):
        return self.role == UserRoles.ADMIN

    @property
    def is_manager(self):
        return self.role in (UserRoles.ADMIN, UserRoles.MANAGER)
