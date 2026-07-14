from django.db import models
from django.utils import timezone


# =============================================================================
# Timestamp Mixin
# =============================================================================

class TimestampMixin(models.Model):
    """Adds created_at and updated_at auto-managed fields."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


# =============================================================================
# Soft Delete Mixin
# =============================================================================

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def hard_deleted(self):
        return super().get_queryset().filter(is_deleted=True)

    def all_with_deleted(self):
        return super().get_queryset()


class SoftDeleteUserManager(SoftDeleteManager):
    """UserManager + SoftDelete: skips deleted users by default, keeps auth methods."""
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return super().get_queryset().get(username=username)

    def get_natural_key(self, obj):
        return (obj.username,)


class SoftDeleteMixin(models.Model):
    """Soft delete support — records are never actually removed from DB."""
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

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


# =============================================================================
# Active Mixin
# =============================================================================

class ActiveMixin(models.Model):
    """Simple is_active toggle for enabling/disabling records."""
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


# =============================================================================
# Note Mixin
# =============================================================================

class NoteMixin(models.Model):
    """Optional notes field for any model."""
    notes = models.TextField(blank=True, default="")

    class Meta:
        abstract = True


# =============================================================================
# Orderable Mixin
# =============================================================================

class OrderableMixin(models.Model):
    """Reorderable records via a sort_order field."""
    sort_order = models.IntegerField(default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["sort_order"]


# =============================================================================
# Slug Mixin
# =============================================================================

class SlugMixin(models.Model):
    """Auto-generate a slug from the `name` field. Override generate_slug() for custom logic."""
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    class Meta:
        abstract = True

    def generate_slug(self):
        from django.utils.text import slugify
        return slugify(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)
