from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import F

from .models import StockMovement, LowStockAlert
from .forms import StockAdjustmentForm
from products.models import Product, Category

User = get_user_model()


_product_counter = 0


def make_product(**kwargs):
    global _product_counter
    _product_counter += 1
    category, _ = Category.objects.get_or_create(
        name="Default", slug="default",
        defaults={"description": "Test category"},
    )
    defaults = {
        "name": f"Widget{_product_counter}",
        "slug": f"widget{_product_counter}",
        "sku": f"W{_product_counter:04d}",
        "cost_price": Decimal("10.00"),
        "selling_price": Decimal("20.00"),
        "stock_quantity": 50,
        "low_stock_threshold": 10,
        "category": category,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


def make_movement(**kwargs):
    product = kwargs.pop("product", None) or make_product()
    defaults = {
        "product": product,
        "movement_type": StockMovement.MovementType.RECEIVED,
        "quantity": 10,
        "running_stock": product.stock_quantity,
    }
    defaults.update(kwargs)
    return StockMovement.objects.create(**defaults)


def make_alert(**kwargs):
    product = kwargs.pop("product", None) or make_product()
    defaults = {
        "product": product,
        "current_stock": product.stock_quantity,
        "threshold": product.low_stock_threshold,
        "status": LowStockAlert.Status.PENDING,
    }
    defaults.update(kwargs)
    return LowStockAlert.objects.create(**defaults)


# =============================================================================
# Model Tests - StockMovement
# =============================================================================

class StockMovementModelTest(TestCase):
    def test_str(self):
        m = make_movement(movement_type="received", quantity=10)
        self.assertIn("Widget", str(m))
        self.assertIn("Received", str(m))
        self.assertIn("+10", str(m))

    def test_str_negative(self):
        m = make_movement(movement_type="sold", quantity=-5)
        self.assertIn("-5", str(m))

    def test_direction_in(self):
        m = make_movement(quantity=10)
        self.assertEqual(m.direction, "IN")

    def test_direction_out(self):
        m = make_movement(quantity=-5)
        self.assertEqual(m.direction, "OUT")

    def test_movement_type_choices(self):
        for choice in StockMovement.MovementType:
            m = make_movement(movement_type=choice, quantity=1)
            self.assertEqual(m.movement_type, choice)

    def test_ordering(self):
        m1 = make_movement(quantity=1)
        m2 = make_movement(quantity=2)
        movements = list(StockMovement.objects.all())
        self.assertEqual(movements[0].quantity, 2)

    def test_performed_by_nullable(self):
        m = make_movement()
        self.assertIsNone(m.performed_by)

    def test_performed_by_set(self):
        user = User.objects.create_user(username="staff", password="pass123")
        m = make_movement(performed_by=user)
        self.assertEqual(m.performed_by, user)

    def test_reference_optional(self):
        m = make_movement(reference="")
        self.assertEqual(m.reference, "")


# =============================================================================
# Model Tests - LowStockAlert
# =============================================================================

class LowStockAlertModelTest(TestCase):
    def test_str(self):
        a = make_alert()
        self.assertIn("Widget", str(a))
        self.assertIn("Low stock", str(a))

    def test_status_choices(self):
        for choice in LowStockAlert.Status:
            a = make_alert(status=choice)
            self.assertEqual(a.status, choice)

    def test_ordering(self):
        a1 = make_alert()
        a2 = make_alert()
        alerts = list(LowStockAlert.objects.all())
        self.assertEqual(alerts[0].pk, a2.pk)

    def test_default_status(self):
        a = LowStockAlert(product=make_product(), current_stock=5, threshold=10)
        a.save()
        self.assertEqual(a.status, LowStockAlert.Status.PENDING)


# =============================================================================
# Form Tests
# =============================================================================

class StockAdjustmentFormTest(TestCase):
    def test_valid_data(self):
        product = make_product()
        form = StockAdjustmentForm(data={
            "product": product.pk,
            "movement_type": "received",
            "quantity": 10,
            "reference": "INV-001",
            "notes": "Restocked",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_quantity_zero_invalid(self):
        product = make_product()
        form = StockAdjustmentForm(data={
            "product": product.pk,
            "movement_type": "received",
            "quantity": 0,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)

    def test_quantity_positive_valid(self):
        product = make_product()
        form = StockAdjustmentForm(data={
            "product": product.pk,
            "movement_type": "received",
            "quantity": 10,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_quantity_negative_valid(self):
        product = make_product()
        form = StockAdjustmentForm(data={
            "product": product.pk,
            "movement_type": "sold",
            "quantity": -5,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_reference_optional(self):
        product = make_product()
        form = StockAdjustmentForm(data={
            "product": product.pk,
            "movement_type": "received",
            "quantity": 5,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_notes_optional(self):
        product = make_product()
        form = StockAdjustmentForm(data={
            "product": product.pk,
            "movement_type": "received",
            "quantity": 5,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_product(self):
        form = StockAdjustmentForm(data={
            "movement_type": "received",
            "quantity": 5,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("product", form.errors)

    def test_missing_movement_type(self):
        product = make_product()
        form = StockAdjustmentForm(data={
            "product": product.pk,
            "quantity": 5,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("movement_type", form.errors)

    def test_inactive_product_excluded(self):
        active = make_product(name="Active", slug="active", sku="A1", stock_quantity=50)
        inactive = make_product(name="Inactive", slug="inactive", sku="I1", stock_quantity=50, is_active=False)
        form = StockAdjustmentForm()
        pks = list(form.fields["product"].queryset.values_list("pk", flat=True))
        self.assertIn(active.pk, pks)
        self.assertNotIn(inactive.pk, pks)


# =============================================================================
# Auth Tests
# =============================================================================

class InventoryAuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_requires_login(self):
        self.assertEqual(self.client.get(reverse("inventory:dashboard")).status_code, 302)

    def test_movement_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("inventory:movement_list")).status_code, 302)

    def test_stock_adjust_requires_login(self):
        self.assertEqual(self.client.get(reverse("inventory:stock_adjust")).status_code, 302)

    def test_alert_list_requires_login(self):
        self.assertEqual(self.client.get(reverse("inventory:alert_list")).status_code, 302)

    def test_alert_acknowledge_requires_login(self):
        a = make_alert()
        self.assertEqual(self.client.post(reverse("inventory:alert_acknowledge", args=[a.pk])).status_code, 302)

    def test_alert_resolve_requires_login(self):
        a = make_alert()
        self.assertEqual(self.client.post(reverse("inventory:alert_resolve", args=[a.pk])).status_code, 302)


# =============================================================================
# View Tests - Dashboard
# =============================================================================

class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("inventory:dashboard")

    def test_empty_dashboard(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventory Dashboard")

    def test_counts_products(self):
        make_product(name="P1", slug="p1", sku="S1")
        make_product(name="P2", slug="p2", sku="S2")
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_products"], 2)

    def test_low_stock_count(self):
        make_product(name="Low", slug="low", sku="L1", stock_quantity=5, low_stock_threshold=10)
        make_product(name="OK", slug="ok", sku="O1", stock_quantity=50, low_stock_threshold=10)
        response = self.client.get(self.url)
        self.assertEqual(response.context["low_stock_count"], 1)

    def test_out_of_stock_count(self):
        make_product(name="Out", slug="out", sku="O2", stock_quantity=0)
        make_product(name="In", slug="in", sku="I2", stock_quantity=10)
        response = self.client.get(self.url)
        self.assertEqual(response.context["out_of_stock_count"], 1)

    def test_pending_alerts_count(self):
        make_alert()
        make_alert(status="acknowledged")
        make_alert(status="resolved")
        response = self.client.get(self.url)
        self.assertEqual(response.context["pending_alerts_count"], 1)


# =============================================================================
# View Tests - Movement List
# =============================================================================

class MovementListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("inventory:movement_list")

    def test_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_movements(self):
        p = make_product(name="Widget", slug="w", sku="W1")
        make_movement(product=p, quantity=10)
        make_movement(product=p, quantity=-5)
        response = self.client.get(self.url)
        self.assertContains(response, "Widget")

    def test_search_by_product_name(self):
        p1 = make_product(name="Alpha", slug="a", sku="A1")
        p2 = make_product(name="Beta", slug="b", sku="B1")
        make_movement(product=p1, quantity=10)
        make_movement(product=p2, quantity=10)
        response = self.client.get(f"{self.url}?search=Alpha")
        content = response.content.decode()
        self.assertIn("Alpha", content)

    def test_search_by_sku(self):
        p = make_product(name="X", slug="x", sku="FINDME")
        make_movement(product=p, quantity=10)
        response = self.client.get(f"{self.url}?search=FINDME")
        self.assertContains(response, "X")

    def test_search_by_reference(self):
        p = make_product(name="Y", slug="y", sku="Y1")
        make_movement(product=p, quantity=10, reference="INV-999")
        response = self.client.get(f"{self.url}?search=INV-999")
        self.assertContains(response, "Y")

    def test_filter_by_type(self):
        p = make_product(name="Z", slug="z", sku="Z1")
        make_movement(product=p, movement_type="received", quantity=10)
        make_movement(product=p, movement_type="sold", quantity=-5)
        response = self.client.get(f"{self.url}?type=received")
        content = response.content.decode()
        self.assertIn("Received", content)

    def test_sort_by_quantity(self):
        p = make_product(name="S", slug="s", sku="S1")
        make_movement(product=p, quantity=100)
        make_movement(product=p, quantity=1)
        response = self.client.get(f"{self.url}?sort=-quantity")
        content = response.content.decode()
        pos_100 = content.find("100")
        pos_1 = content.find("+1")
        self.assertLess(pos_100, pos_1)


# =============================================================================
# View Tests - Stock Adjust
# =============================================================================

class StockAdjustViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("inventory:stock_adjust")
        self.product = make_product(stock_quantity=50)

    def test_get_returns_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stock Adjustment")

    def test_post_creates_movement(self):
        response = self.client.post(self.url, {
            "product": self.product.pk,
            "movement_type": "received",
            "quantity": 10,
            "reference": "INV-001",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StockMovement.objects.count(), 1)
        m = StockMovement.objects.first()
        self.assertEqual(m.quantity, 10)
        self.assertEqual(m.performed_by, self.user)

    def test_post_updates_product_stock(self):
        self.client.post(self.url, {
            "product": self.product.pk,
            "movement_type": "received",
            "quantity": 10,
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 60)

    def test_post_negative_quantity(self):
        self.client.post(self.url, {
            "product": self.product.pk,
            "movement_type": "sold",
            "quantity": -5,
        })
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 45)

    def test_post_sets_running_stock(self):
        self.client.post(self.url, {
            "product": self.product.pk,
            "movement_type": "received",
            "quantity": 10,
        })
        m = StockMovement.objects.first()
        self.assertEqual(m.running_stock, 60)

    def test_post_redirects_to_movement_list(self):
        response = self.client.post(self.url, {
            "product": self.product.pk,
            "movement_type": "received",
            "quantity": 5,
        })
        self.assertRedirects(response, reverse("inventory:movement_list"))

    def test_post_creates_low_stock_alert(self):
        product = make_product(name="Low", slug="low", sku="L1",
                               stock_quantity=15, low_stock_threshold=10)
        self.client.post(self.url, {
            "product": product.pk,
            "movement_type": "sold",
            "quantity": -10,
        })
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 5)
        self.assertTrue(LowStockAlert.objects.filter(product=product, status="pending").exists())

    def test_post_no_alert_when_stock_ok(self):
        self.client.post(self.url, {
            "product": self.product.pk,
            "movement_type": "received",
            "quantity": 10,
        })
        self.assertFalse(LowStockAlert.objects.filter(product=self.product).exists())

    def test_post_invalid_returns_form(self):
        response = self.client.post(self.url, {"quantity": 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StockMovement.objects.count(), 0)


# =============================================================================
# View Tests - Alert List
# =============================================================================

class AlertListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.url = reverse("inventory:alert_list")

    def test_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_default_excludes_resolved(self):
        make_alert()
        make_alert(status="resolved")
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["alerts"]), 1)

    def test_filter_by_status(self):
        make_alert()
        make_alert(status="acknowledged")
        response = self.client.get(f"{self.url}?status=pending")
        self.assertEqual(len(response.context["alerts"]), 1)

    def test_filter_all_statuses(self):
        make_alert()
        make_alert(status="acknowledged")
        make_alert(status="resolved")
        response = self.client.get(f"{self.url}?status=resolved")
        self.assertEqual(len(response.context["alerts"]), 1)


# =============================================================================
# View Tests - Alert Actions
# =============================================================================

class AlertAcknowledgeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.alert = make_alert()

    def test_post_acknowledges(self):
        response = self.client.post(reverse("inventory:alert_acknowledge", args=[self.alert.pk]))
        self.assertEqual(response.status_code, 302)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, "acknowledged")

    def test_get_not_allowed(self):
        response = self.client.get(reverse("inventory:alert_acknowledge", args=[self.alert.pk]))
        self.assertEqual(response.status_code, 405)

    def test_redirects_to_alert_list(self):
        response = self.client.post(reverse("inventory:alert_acknowledge", args=[self.alert.pk]))
        self.assertRedirects(response, reverse("inventory:alert_list"))


class AlertResolveViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="admin", password="pass123")
        self.client.force_login(self.user)
        self.alert = make_alert()

    def test_post_resolves(self):
        response = self.client.post(reverse("inventory:alert_resolve", args=[self.alert.pk]))
        self.assertEqual(response.status_code, 302)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, "resolved")

    def test_get_not_allowed(self):
        response = self.client.get(reverse("inventory:alert_resolve", args=[self.alert.pk]))
        self.assertEqual(response.status_code, 405)

    def test_redirects_to_alert_list(self):
        response = self.client.post(reverse("inventory:alert_resolve", args=[self.alert.pk]))
        self.assertRedirects(response, reverse("inventory:alert_list"))


# =============================================================================
# URL Resolution Tests
# =============================================================================

class InventoryURLTest(TestCase):
    def test_dashboard(self):
        self.assertEqual(reverse("inventory:dashboard"), "/inventory/")

    def test_movement_list(self):
        self.assertEqual(reverse("inventory:movement_list"), "/inventory/movements/")

    def test_stock_adjust(self):
        self.assertEqual(reverse("inventory:stock_adjust"), "/inventory/adjust/")

    def test_alert_list(self):
        self.assertEqual(reverse("inventory:alert_list"), "/inventory/alerts/")

    def test_alert_acknowledge(self):
        self.assertEqual(reverse("inventory:alert_acknowledge", args=[1]), "/inventory/alerts/1/acknowledge/")

    def test_alert_resolve(self):
        self.assertEqual(reverse("inventory:alert_resolve", args=[1]), "/inventory/alerts/1/resolve/")
