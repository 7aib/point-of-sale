from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Discount, Coupon
from .forms import DiscountForm, CouponForm
from products.models import Product, Category

User = get_user_model()


def make_product(**kwargs):
    category, _ = Category.objects.get_or_create(
        name="Default", slug="default",
        defaults={"description": "Test category"},
    )
    defaults = {
        "name": "Widget", "slug": "widget", "sku": "W001",
        "cost_price": Decimal("10.00"), "selling_price": Decimal("20.00"),
        "stock_quantity": 100, "category": category,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def make_discount(**kwargs):
    defaults = {
        "name": "Summer Sale", "code": "SUMMER20",
        "discount_type": Discount.DiscountType.PERCENTAGE,
        "value": Decimal("20.00"),
        "valid_from": timezone.now() - timedelta(days=1),
        "valid_to": timezone.now() + timedelta(days=30),
        "is_active": True,
    }
    defaults.update(kwargs)
    return Discount.objects.create(**defaults)


def make_coupon(**kwargs):
    defaults = {
        "code": "SAVE10",
        "discount_type": Discount.DiscountType.PERCENTAGE,
        "discount_value": Decimal("10.00"),
        "valid_from": timezone.now() - timedelta(days=1),
        "valid_to": timezone.now() + timedelta(days=30),
        "is_active": True,
    }
    defaults.update(kwargs)
    return Coupon.objects.create(**defaults)


DISCOUNT_FORM_DATA = {
    "name": "Test Discount",
    "code": "TST10",
    "discount_type": "percentage",
    "value": "10.00",
    "min_purchase_amount": "0",
    "max_discount_amount": "0",
    "usage_limit": "0",
    "valid_from": timezone.now().strftime("%Y-%m-%dT%H:%M"),
    "is_active": True,
}

COUPON_FORM_DATA = {
    "code": "TSTCOUP",
    "discount_type": "percentage",
    "discount_value": "10",
    "max_uses": "0",
    "max_uses_per_user": "1",
    "min_order_amount": "0",
    "valid_from": timezone.now().strftime("%Y-%m-%dT%H:%M"),
    "is_active": True,
}


# =============================================================================
# Model Tests - Discount
# =============================================================================

class DiscountModelTest(TestCase):
    def test_str_percentage(self):
        d = make_discount(name="Summer", code="SUM", value=Decimal("20"))
        self.assertIn("Summer", str(d))
        self.assertIn("20%", str(d))

    def test_str_fixed(self):
        d = make_discount(
            name="Fixed", code="FIX",
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("50"),
        )
        self.assertIn("Fixed", str(d))
        self.assertIn("50", str(d))

    def test_clean_percentage_exceeds_100(self):
        d = make_discount(code="BAD1")
        d.value = Decimal("150")
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean_value_zero(self):
        d = make_discount(code="BAD2")
        d.value = Decimal("0")
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean_value_negative(self):
        d = make_discount(code="BAD3")
        d.value = Decimal("-5")
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean_valid_to_before_valid_from(self):
        with self.assertRaises(ValidationError):
            make_discount(
                code="BADOOPS",
                valid_from=timezone.now(),
                valid_to=timezone.now() - timedelta(days=1),
            )

    def test_save_calls_full_clean(self):
        d = Discount(
            name="Test", code="CLEAN", value=Decimal("10"),
            discount_type=Discount.DiscountType.PERCENTAGE,
        )
        d.save()
        d.refresh_from_db()
        self.assertEqual(d.name, "Test")

    def test_is_valid_active_within_dates(self):
        d = make_discount()
        self.assertTrue(d.is_valid)

    def test_is_valid_inactive(self):
        d = make_discount(is_active=False)
        self.assertFalse(d.is_valid)

    def test_is_valid_not_yet_started(self):
        d = make_discount(
            valid_from=timezone.now() + timedelta(days=10),
            valid_to=timezone.now() + timedelta(days=30),
        )
        self.assertFalse(d.is_valid)

    def test_is_valid_expired(self):
        d = make_discount(
            valid_from=timezone.now() - timedelta(days=30),
            valid_to=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(d.is_valid)

    def test_is_valid_no_expiry(self):
        d = make_discount(valid_to=None)
        self.assertTrue(d.is_valid)

    def test_is_valid_usage_exhausted(self):
        d = make_discount(usage_limit=5, used_count=5)
        self.assertFalse(d.is_valid)

    def test_is_valid_usage_remaining(self):
        d = make_discount(usage_limit=10, used_count=3)
        self.assertTrue(d.is_valid)

    def test_is_expired_false_no_expiry(self):
        d = make_discount(valid_to=None)
        self.assertFalse(d.is_expired)

    def test_is_expired_true(self):
        d = make_discount(
            valid_to=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(d.is_expired)

    def test_usage_remaining_unlimited(self):
        d = make_discount(usage_limit=0)
        self.assertIsNone(d.usage_remaining)

    def test_usage_remaining_limited(self):
        d = make_discount(usage_limit=10, used_count=3)
        self.assertEqual(d.usage_remaining, 7)

    def test_usage_remaining_exhausted(self):
        d = make_discount(usage_limit=5, used_count=10)
        self.assertEqual(d.usage_remaining, 0)

    def test_get_display_value_percentage(self):
        d = make_discount(value=Decimal("25"))
        self.assertEqual(d.get_display_value(), "25%")

    def test_get_display_value_fixed(self):
        d = make_discount(
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("50"),
        )
        self.assertIn("50", d.get_display_value())

    def test_calculate_discount_percentage(self):
        d = make_discount(value=Decimal("20"))
        result = d.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("20.00"))

    def test_calculate_discount_fixed(self):
        d = make_discount(
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("25"),
        )
        result = d.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("25.00"))

    def test_calculate_discount_fixed_capped_at_subtotal(self):
        d = make_discount(
            discount_type=Discount.DiscountType.FIXED,
            value=Decimal("200"),
        )
        result = d.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("100.00"))

    def test_calculate_discount_percentage_with_max_cap(self):
        d = make_discount(
            value=Decimal("50"),
            max_discount_amount=Decimal("30"),
        )
        result = d.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("30.00"))

    def test_calculate_discount_percentage_below_max_cap(self):
        d = make_discount(
            value=Decimal("10"),
            max_discount_amount=Decimal("30"),
        )
        result = d.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("10.00"))

    def test_calculate_discount_below_min_purchase(self):
        d = make_discount(
            value=Decimal("20"),
            min_purchase_amount=Decimal("50"),
        )
        result = d.calculate_discount(Decimal("30"))
        self.assertEqual(result, 0)

    def test_calculate_discount_at_min_purchase(self):
        d = make_discount(
            value=Decimal("20"),
            min_purchase_amount=Decimal("50"),
        )
        result = d.calculate_discount(Decimal("50"))
        self.assertEqual(result, Decimal("10.00"))

    def test_calculate_discount_invalid(self):
        d = make_discount(is_active=False)
        result = d.calculate_discount(Decimal("100"))
        self.assertEqual(result, 0)

    def test_m2m_products(self):
        d = make_discount()
        p = make_product(name="P1", slug="p1", sku="S1")
        d.applies_to_products.add(p)
        self.assertIn(p, d.applies_to_products.all())

    def test_m2m_categories(self):
        d = make_discount()
        cat = Category.objects.create(name="Cat1", slug="cat1")
        d.applies_to_categories.add(cat)
        self.assertIn(cat, d.applies_to_categories.all())

    def test_ordering(self):
        d1 = make_discount(name="First", code="F1")
        d2 = make_discount(name="Second", code="F2")
        discounts = list(Discount.objects.all())
        self.assertEqual(discounts[0].name, "Second")


# =============================================================================
# Model Tests - Coupon
# =============================================================================

class CouponModelTest(TestCase):
    def test_str(self):
        c = make_coupon(code="SAVE10")
        self.assertIn("SAVE10", str(c))

    def test_str_fixed(self):
        c = make_coupon(
            code="FIX50",
            discount_type=Discount.DiscountType.FIXED,
            discount_value=Decimal("50"),
        )
        self.assertIn("FIX50", str(c))
        self.assertIn("50", str(c))

    def test_clean_percentage_exceeds_100(self):
        c = Coupon(
            code="BAD1", discount_value=Decimal("150"),
            discount_type=Discount.DiscountType.PERCENTAGE,
        )
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_clean_value_zero(self):
        c = Coupon(code="BAD2", discount_value=Decimal("0"))
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_clean_value_negative(self):
        c = Coupon(code="BAD3", discount_value=Decimal("-5"))
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_clean_valid_to_before_valid_from(self):
        with self.assertRaises(ValidationError):
            make_coupon(
                code="BADOOPS",
                valid_from=timezone.now(),
                valid_to=timezone.now() - timedelta(days=1),
            )

    def test_is_valid_active(self):
        c = make_coupon()
        self.assertTrue(c.is_valid)

    def test_is_valid_inactive(self):
        c = make_coupon(is_active=False)
        self.assertFalse(c.is_valid)

    def test_is_valid_not_yet_started(self):
        c = make_coupon(
            valid_from=timezone.now() + timedelta(days=10),
            valid_to=timezone.now() + timedelta(days=30),
        )
        self.assertFalse(c.is_valid)

    def test_is_valid_expired(self):
        c = make_coupon(
            valid_from=timezone.now() - timedelta(days=30),
            valid_to=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(c.is_valid)

    def test_is_valid_usage_exhausted(self):
        c = make_coupon(max_uses=5, used_count=5)
        self.assertFalse(c.is_valid)

    def test_is_expired_false_no_expiry(self):
        c = make_coupon(valid_to=None)
        self.assertFalse(c.is_expired)

    def test_is_expired_true(self):
        c = make_coupon(valid_to=timezone.now() - timedelta(hours=1))
        self.assertTrue(c.is_expired)

    def test_usage_remaining_unlimited(self):
        c = make_coupon(max_uses=0)
        self.assertIsNone(c.usage_remaining)

    def test_usage_remaining_limited(self):
        c = make_coupon(max_uses=10, used_count=3)
        self.assertEqual(c.usage_remaining, 7)

    def test_usage_remaining_exhausted(self):
        c = make_coupon(max_uses=5, used_count=10)
        self.assertEqual(c.usage_remaining, 0)

    def test_get_display_value_percentage(self):
        c = make_coupon(discount_value=Decimal("25"))
        self.assertEqual(c.get_display_value(), "25% off")

    def test_get_display_value_fixed(self):
        c = make_coupon(
            discount_type=Discount.DiscountType.FIXED,
            discount_value=Decimal("50"),
        )
        self.assertIn("50", c.get_display_value())

    def test_calculate_discount_percentage(self):
        c = make_coupon(discount_value=Decimal("20"))
        result = c.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("20.00"))

    def test_calculate_discount_fixed(self):
        c = make_coupon(
            discount_type=Discount.DiscountType.FIXED,
            discount_value=Decimal("25"),
        )
        result = c.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("25.00"))

    def test_calculate_discount_fixed_capped_at_subtotal(self):
        c = make_coupon(
            discount_type=Discount.DiscountType.FIXED,
            discount_value=Decimal("200"),
        )
        result = c.calculate_discount(Decimal("100"))
        self.assertEqual(result, Decimal("100.00"))

    def test_calculate_discount_below_min_order(self):
        c = make_coupon(
            discount_value=Decimal("20"),
            min_order_amount=Decimal("50"),
        )
        result = c.calculate_discount(Decimal("30"))
        self.assertEqual(result, 0)

    def test_calculate_discount_at_min_order(self):
        c = make_coupon(
            discount_value=Decimal("20"),
            min_order_amount=Decimal("50"),
        )
        result = c.calculate_discount(Decimal("50"))
        self.assertEqual(result, Decimal("10.00"))

    def test_calculate_discount_invalid(self):
        c = make_coupon(is_active=False)
        result = c.calculate_discount(Decimal("100"))
        self.assertEqual(result, 0)

    def test_redeem_increments_used_count(self):
        c = make_coupon(used_count=0)
        c.redeem()
        c.refresh_from_db()
        self.assertEqual(c.used_count, 1)

    def test_redeem_multiple_times(self):
        c = make_coupon(used_count=0)
        c.redeem()
        c.redeem()
        c.refresh_from_db()
        self.assertEqual(c.used_count, 2)


# =============================================================================
# Form Tests - DiscountForm
# =============================================================================

class DiscountFormTest(TestCase):
    def test_valid_data(self):
        form = DiscountForm(data=DISCOUNT_FORM_DATA)
        self.assertTrue(form.is_valid(), form.errors)

    def test_code_uppercased(self):
        data = {**DISCOUNT_FORM_DATA, "code": "lowercase"}
        form = DiscountForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        discount = form.save()
        self.assertEqual(discount.code, "LOWERCASE")

    def test_duplicate_code(self):
        make_discount(code="EXISTING")
        data = {**DISCOUNT_FORM_DATA, "code": "existing"}
        form = DiscountForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_duplicate_code_on_edit(self):
        d = make_discount(code="ORIGINAL")
        data = {**DISCOUNT_FORM_DATA, "code": "original"}
        form = DiscountForm(data=data, instance=d)
        self.assertTrue(form.is_valid(), form.errors)

    def test_percentage_over_100(self):
        data = {**DISCOUNT_FORM_DATA, "value": "150"}
        form = DiscountForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("value", form.errors)

    def test_missing_required(self):
        form = DiscountForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("code", form.errors)


# =============================================================================
# Form Tests - CouponForm
# =============================================================================

class CouponFormTest(TestCase):
    def test_valid_data(self):
        form = CouponForm(data=COUPON_FORM_DATA)
        self.assertTrue(form.is_valid(), form.errors)

    def test_code_uppercased(self):
        data = {**COUPON_FORM_DATA, "code": "lowercase"}
        form = CouponForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        coupon = form.save()
        self.assertEqual(coupon.code, "LOWERCASE")

    def test_duplicate_code(self):
        make_coupon(code="EXISTING")
        data = {**COUPON_FORM_DATA, "code": "existing"}
        form = CouponForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_duplicate_code_on_edit(self):
        c = make_coupon(code="ORIGINAL")
        data = {**COUPON_FORM_DATA, "code": "original"}
        form = CouponForm(data=data, instance=c)
        self.assertTrue(form.is_valid(), form.errors)

    def test_percentage_over_100(self):
        data = {**COUPON_FORM_DATA, "discount_value": "150"}
        form = CouponForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("discount_value", form.errors)

    def test_missing_required(self):
        form = CouponForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)


# =============================================================================
# Auth Tests
# =============================================================================

class DiscountAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.d = make_discount()

    def test_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:discount_list")).status_code, 302)

    def test_create_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:discount_create")).status_code, 302)

    def test_detail_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:discount_detail", args=[self.d.pk])).status_code, 302)

    def test_update_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:discount_update", args=[self.d.pk])).status_code, 302)

    def test_delete_requires_login(self):
        self.assertEqual(self.client.post(reverse("discounts:discount_delete", args=[self.d.pk])).status_code, 302)

    def test_toggle_requires_login(self):
        self.assertEqual(self.client.post(reverse("discounts:discount_toggle", args=[self.d.pk])).status_code, 302)


class CouponAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.c = make_coupon()

    def test_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:coupon_list")).status_code, 302)

    def test_create_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:coupon_create")).status_code, 302)

    def test_detail_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:coupon_detail", args=[self.c.pk])).status_code, 302)

    def test_update_requires_login(self):
        self.assertEqual(self.client.get(reverse("discounts:coupon_update", args=[self.c.pk])).status_code, 302)

    def test_delete_requires_login(self):
        self.assertEqual(self.client.post(reverse("discounts:coupon_delete", args=[self.c.pk])).status_code, 302)

    def test_toggle_requires_login(self):
        self.assertEqual(self.client.post(reverse("discounts:coupon_toggle", args=[self.c.pk])).status_code, 302)


# =============================================================================
# View Tests - Discount CRUD
# =============================================================================

class DiscountListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("discounts:discount_list")

    def test_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_discounts(self):
        make_discount(name="Sale1", code="S1")
        make_discount(name="Sale2", code="S2")
        response = self.client.get(self.url)
        self.assertContains(response, "Sale1")
        self.assertContains(response, "Sale2")

    def test_search_by_name(self):
        make_discount(name="Summer", code="SUM")
        make_discount(name="Winter", code="WIN")
        response = self.client.get(f"{self.url}?search=Summer")
        content = response.content.decode()
        self.assertIn("Summer", content)
        self.assertNotIn("/discounts/2/", content)

    def test_search_by_code(self):
        make_discount(name="A", code="CODEA")
        make_discount(name="B", code="CODEB")
        response = self.client.get(f"{self.url}?search=CODEA")
        content = response.content.decode()
        self.assertIn("CODEA", content)
        self.assertNotIn("CODEB", content)

    def test_filter_by_type_percentage(self):
        make_discount(name="Pct", code="P1", discount_type="percentage", value=Decimal("10"))
        make_discount(name="Fix", code="F1", discount_type="fixed", value=Decimal("10"))
        response = self.client.get(f"{self.url}?type=percentage")
        content = response.content.decode()
        self.assertIn("/discounts/1/", content)
        self.assertNotIn("/discounts/2/", content)

    def test_filter_by_type_fixed(self):
        make_discount(name="Pct", code="P2", discount_type="percentage", value=Decimal("10"))
        make_discount(name="Fix", code="F2", discount_type="fixed", value=Decimal("10"))
        response = self.client.get(f"{self.url}?type=fixed")
        content = response.content.decode()
        self.assertIn("/discounts/2/", content)
        self.assertNotIn("/discounts/1/", content)

    def test_filter_by_status_active(self):
        d1 = make_discount(name="Active1", code="A1", is_active=True)
        d2 = make_discount(name="Inactive1", code="I1", is_active=False)
        response = self.client.get(f"{self.url}?status=active")
        content = response.content.decode()
        self.assertIn(f"/discounts/{d1.pk}/", content)
        self.assertNotIn(f"/discounts/{d2.pk}/", content)

    def test_filter_by_status_inactive(self):
        d1 = make_discount(name="Active2", code="A2", is_active=True)
        d2 = make_discount(name="Inactive2", code="I2", is_active=False)
        response = self.client.get(f"{self.url}?status=inactive")
        content = response.content.decode()
        self.assertIn(f"/discounts/{d2.pk}/", content)
        self.assertNotIn(f"/discounts/{d1.pk}/", content)

    def test_filter_by_status_expired(self):
        d1 = make_discount(name="Expired1", code="E1",
                           valid_from=timezone.now() - timedelta(days=30),
                           valid_to=timezone.now() - timedelta(days=1))
        d2 = make_discount(name="Valid1", code="V1",
                           valid_to=timezone.now() + timedelta(days=1))
        response = self.client.get(f"{self.url}?status=expired")
        content = response.content.decode()
        self.assertIn(f"/discounts/{d1.pk}/", content)
        self.assertNotIn(f"/discounts/{d2.pk}/", content)

    def test_sort_by_name(self):
        make_discount(name="Zebra", code="Z1")
        make_discount(name="Alpha", code="A1")
        response = self.client.get(f"{self.url}?sort=name")
        content = response.content.decode()
        alpha_pos = content.find("Alpha")
        zebra_pos = content.find("Zebra")
        self.assertLess(alpha_pos, zebra_pos)


class DiscountCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("discounts:discount_create")

    def test_get_returns_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Discount")

    def test_post_creates_discount(self):
        response = self.client.post(self.url, DISCOUNT_FORM_DATA)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Discount.objects.filter(code="TST10").exists())

    def test_post_redirects_to_list(self):
        response = self.client.post(self.url, DISCOUNT_FORM_DATA)
        self.assertRedirects(response, reverse("discounts:discount_list"))

    def test_post_invalid_returns_form(self):
        response = self.client.post(self.url, {"name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Discount.objects.exists())


class DiscountDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.d = make_discount(name="DetailTest")

    def test_detail_page(self):
        response = self.client.get(reverse("discounts:discount_detail", args=[self.d.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DetailTest")

    def test_detail_404(self):
        response = self.client.get(reverse("discounts:discount_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


class DiscountUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.d = make_discount(name="OldName", code="OLD1")

    def test_get_returns_form(self):
        response = self.client.get(reverse("discounts:discount_update", args=[self.d.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit")

    def test_post_updates(self):
        data = {**DISCOUNT_FORM_DATA, "code": "OLD1"}
        response = self.client.post(reverse("discounts:discount_update", args=[self.d.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.d.refresh_from_db()
        self.assertEqual(self.d.name, "Test Discount")

    def test_post_redirects_to_detail(self):
        data = {**DISCOUNT_FORM_DATA, "code": "OLD1"}
        response = self.client.post(reverse("discounts:discount_update", args=[self.d.pk]), data)
        self.assertRedirects(response, reverse("discounts:discount_detail", args=[self.d.pk]))

    def test_invalid_returns_form(self):
        response = self.client.post(reverse("discounts:discount_update", args=[self.d.pk]), {"name": ""})
        self.assertEqual(response.status_code, 200)
        self.d.refresh_from_db()
        self.assertEqual(self.d.name, "OldName")


class DiscountDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.d = make_discount(code="DEL1")

    def test_post_deletes(self):
        response = self.client.post(reverse("discounts:discount_delete", args=[self.d.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Discount.objects.filter(pk=self.d.pk).exists())

    def test_get_not_allowed(self):
        response = self.client.get(reverse("discounts:discount_delete", args=[self.d.pk]))
        self.assertEqual(response.status_code, 405)

    def test_404_already_deleted(self):
        pk = self.d.pk
        self.d.delete()
        response = self.client.post(reverse("discounts:discount_delete", args=[pk]))
        self.assertEqual(response.status_code, 404)


class DiscountToggleViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.d = make_discount(is_active=True)

    def test_toggle_off(self):
        response = self.client.post(reverse("discounts:discount_toggle", args=[self.d.pk]))
        self.assertEqual(response.status_code, 302)
        self.d.refresh_from_db()
        self.assertFalse(self.d.is_active)

    def test_toggle_on(self):
        self.d.is_active = False
        self.d.save(update_fields=["is_active"])
        response = self.client.post(reverse("discounts:discount_toggle", args=[self.d.pk]))
        self.assertEqual(response.status_code, 302)
        self.d.refresh_from_db()
        self.assertTrue(self.d.is_active)

    def test_get_not_allowed(self):
        response = self.client.get(reverse("discounts:discount_toggle", args=[self.d.pk]))
        self.assertEqual(response.status_code, 405)


# =============================================================================
# View Tests - Coupon CRUD
# =============================================================================

class CouponListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("discounts:coupon_list")

    def test_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_coupons(self):
        make_coupon(code="C1")
        make_coupon(code="C2")
        response = self.client.get(self.url)
        self.assertContains(response, "C1")
        self.assertContains(response, "C2")

    def test_search_by_code(self):
        make_coupon(code="FINDME")
        make_coupon(code="NOPE")
        response = self.client.get(f"{self.url}?search=FINDME")
        content = response.content.decode()
        self.assertIn("FINDME", content)
        self.assertNotIn("NOPE", content)

    def test_filter_by_type_percentage(self):
        make_coupon(code="P1", discount_type="percentage", discount_value=Decimal("10"))
        make_coupon(code="F1", discount_type="fixed", discount_value=Decimal("10"))
        response = self.client.get(f"{self.url}?type=percentage")
        content = response.content.decode()
        self.assertIn("P1", content)
        self.assertNotIn("F1", content)

    def test_filter_by_status_active(self):
        make_coupon(code="A1", is_active=True)
        make_coupon(code="I1", is_active=False)
        response = self.client.get(f"{self.url}?status=active")
        content = response.content.decode()
        self.assertIn("A1", content)
        self.assertNotIn("I1", content)


class CouponCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("discounts:coupon_create")

    def test_get_returns_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Coupon")

    def test_post_creates_coupon(self):
        response = self.client.post(self.url, COUPON_FORM_DATA)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Coupon.objects.filter(code="TSTCOUP").exists())

    def test_post_redirects_to_list(self):
        response = self.client.post(self.url, COUPON_FORM_DATA)
        self.assertRedirects(response, reverse("discounts:coupon_list"))

    def test_post_invalid_returns_form(self):
        response = self.client.post(self.url, {"code": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Coupon.objects.exists())


class CouponDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.c = make_coupon(code="DET1")

    def test_detail_page(self):
        response = self.client.get(reverse("discounts:coupon_detail", args=[self.c.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DET1")

    def test_detail_404(self):
        response = self.client.get(reverse("discounts:coupon_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


class CouponUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.c = make_coupon(code="UPD1")

    def test_get_returns_form(self):
        response = self.client.get(reverse("discounts:coupon_update", args=[self.c.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit")

    def test_post_updates(self):
        data = {**COUPON_FORM_DATA, "code": "UPD1", "discount_value": "25"}
        response = self.client.post(reverse("discounts:coupon_update", args=[self.c.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.c.refresh_from_db()
        self.assertEqual(self.c.discount_value, Decimal("25"))

    def test_invalid_returns_form(self):
        response = self.client.post(reverse("discounts:coupon_update", args=[self.c.pk]), {"code": ""})
        self.assertEqual(response.status_code, 200)


class CouponDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.c = make_coupon(code="DEL2")

    def test_post_deletes(self):
        response = self.client.post(reverse("discounts:coupon_delete", args=[self.c.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Coupon.objects.filter(pk=self.c.pk).exists())

    def test_get_not_allowed(self):
        response = self.client.get(reverse("discounts:coupon_delete", args=[self.c.pk]))
        self.assertEqual(response.status_code, 405)


class CouponToggleViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.c = make_coupon(is_active=True)

    def test_toggle_off(self):
        response = self.client.post(reverse("discounts:coupon_toggle", args=[self.c.pk]))
        self.assertEqual(response.status_code, 302)
        self.c.refresh_from_db()
        self.assertFalse(self.c.is_active)

    def test_toggle_on(self):
        self.c.is_active = False
        self.c.save(update_fields=["is_active"])
        response = self.client.post(reverse("discounts:coupon_toggle", args=[self.c.pk]))
        self.assertEqual(response.status_code, 302)
        self.c.refresh_from_db()
        self.assertTrue(self.c.is_active)

    def test_get_not_allowed(self):
        response = self.client.get(reverse("discounts:coupon_toggle", args=[self.c.pk]))
        self.assertEqual(response.status_code, 405)


# =============================================================================
# URL Resolution Tests
# =============================================================================

class DiscountURLTest(TestCase):
    def test_discount_list(self):
        self.assertEqual(reverse("discounts:discount_list"), "/discounts/")

    def test_discount_create(self):
        self.assertEqual(reverse("discounts:discount_create"), "/discounts/add/")

    def test_discount_detail(self):
        self.assertEqual(reverse("discounts:discount_detail", args=[1]), "/discounts/1/")

    def test_discount_update(self):
        self.assertEqual(reverse("discounts:discount_update", args=[1]), "/discounts/1/edit/")

    def test_discount_delete(self):
        self.assertEqual(reverse("discounts:discount_delete", args=[1]), "/discounts/1/delete/")

    def test_discount_toggle(self):
        self.assertEqual(reverse("discounts:discount_toggle", args=[1]), "/discounts/1/toggle/")

    def test_coupon_list(self):
        self.assertEqual(reverse("discounts:coupon_list"), "/discounts/coupons/")

    def test_coupon_create(self):
        self.assertEqual(reverse("discounts:coupon_create"), "/discounts/coupons/add/")

    def test_coupon_detail(self):
        self.assertEqual(reverse("discounts:coupon_detail", args=[1]), "/discounts/coupons/1/")

    def test_coupon_update(self):
        self.assertEqual(reverse("discounts:coupon_update", args=[1]), "/discounts/coupons/1/edit/")

    def test_coupon_delete(self):
        self.assertEqual(reverse("discounts:coupon_delete", args=[1]), "/discounts/coupons/1/delete/")

    def test_coupon_toggle(self):
        self.assertEqual(reverse("discounts:coupon_toggle", args=[1]), "/discounts/coupons/1/toggle/")
