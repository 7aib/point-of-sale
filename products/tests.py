from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from config import PRODUCTS_PER_PAGE

from .models import Category, Product
from .forms import CategoryForm, ProductForm

User = get_user_model()


# =============================================================================
# Factories
# =============================================================================

_category_counter = 0


def make_category(**kwargs):
    global _category_counter
    _category_counter += 1
    defaults = {
        "name": f"Cat{_category_counter}",
        "slug": f"cat{_category_counter}",
    }
    defaults.update(kwargs)
    return Category.objects.create(**defaults)


_product_counter = 0


def make_product(**kwargs):
    global _product_counter
    _product_counter += 1
    category = kwargs.pop("category", None)
    if category is None:
        category = make_category()
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


# =============================================================================
# Model Tests — Category
# =============================================================================

class CategoryModelTest(TestCase):
    def test_str(self):
        c = make_category(name="Electronics")
        self.assertEqual(str(c), "Electronics")

    def test_save_auto_slug(self):
        c = Category.objects.create(name="Clothing")
        self.assertEqual(c.slug, "clothing")

    def test_save_preserves_manual_slug(self):
        c = make_category(name="Shoes", slug="my-shoes")
        self.assertEqual(c.slug, "my-shoes")

    def test_ordering(self):
        c2 = make_category(name="B", sort_order=2)
        c1 = make_category(name="A", sort_order=1)
        cats = list(Category.objects.all())
        self.assertEqual(cats[0], c1)
        self.assertEqual(cats[1], c2)

    def test_level_root(self):
        c = make_category()
        self.assertEqual(c.level, 0)

    def test_level_child(self):
        parent = make_category()
        child = make_category(parent=parent)
        self.assertEqual(child.level, 1)

    def test_level_grandchild(self):
        grandparent = make_category()
        parent = make_category(parent=grandparent)
        child = make_category(parent=parent)
        self.assertEqual(child.level, 2)

    def test_get_ancestors_root(self):
        c = make_category()
        self.assertEqual(c.get_ancestors, [])

    def test_get_ancestors_child(self):
        parent = make_category()
        child = make_category(parent=parent)
        self.assertEqual(child.get_ancestors, [parent])

    def test_get_ancestors_grandchild(self):
        gp = make_category()
        p = make_category(parent=gp)
        c = make_category(parent=p)
        self.assertEqual(c.get_ancestors, [gp, p])

    def test_full_name_root(self):
        c = make_category(name="Electronics")
        self.assertEqual(c.full_name, "Electronics")

    def test_full_name_nested(self):
        gp = make_category(name="A")
        p = make_category(name="B", parent=gp)
        c = make_category(name="C", parent=p)
        self.assertEqual(c.full_name, "A > B > C")

    def test_children_related_name(self):
        parent = make_category()
        make_category(parent=parent)
        make_category(parent=parent)
        self.assertEqual(parent.children.count(), 2)

    def test_meta_ordering(self):
        self.assertEqual(Category._meta.ordering, ["sort_order", "name"])


# =============================================================================
# Model Tests — Product
# =============================================================================

class ProductModelTest(TestCase):
    def test_str(self):
        p = make_product(name="Widget", sku="W001")
        self.assertEqual(str(p), "Widget (W001)")

    def test_save_auto_slug(self):
        p = Product.objects.create(
            name="Gadget", slug="", sku="G001",
            cost_price=Decimal("5.00"), selling_price=Decimal("10.00"),
            category=make_category(),
        )
        self.assertEqual(p.slug, "gadget")

    def test_save_preserves_manual_slug(self):
        p = make_product(name="X", slug="my-slug")
        self.assertEqual(p.slug, "my-slug")

    def test_is_in_stock_true(self):
        p = make_product(stock_quantity=10)
        self.assertTrue(p.is_in_stock)

    def test_is_in_stock_false(self):
        p = make_product(stock_quantity=0)
        self.assertFalse(p.is_in_stock)

    def test_is_low_stock_true(self):
        p = make_product(stock_quantity=5, low_stock_threshold=10)
        self.assertTrue(p.is_low_stock)

    def test_is_low_stock_false(self):
        p = make_product(stock_quantity=20, low_stock_threshold=10)
        self.assertFalse(p.is_low_stock)

    def test_is_low_stock_equal(self):
        p = make_product(stock_quantity=10, low_stock_threshold=10)
        self.assertTrue(p.is_low_stock)

    def test_profit_margin(self):
        p = make_product(cost_price=Decimal("10.00"), selling_price=Decimal("20.00"))
        self.assertEqual(p.profit_margin, 50.0)

    def test_profit_margin_zero_selling_price(self):
        p = make_product(cost_price=Decimal("10.00"), selling_price=Decimal("0.00"))
        self.assertEqual(p.profit_margin, 0)

    def test_profit_per_unit(self):
        p = make_product(cost_price=Decimal("7.50"), selling_price=Decimal("20.00"))
        self.assertEqual(p.profit_per_unit, Decimal("12.50"))

    def test_soft_delete(self):
        p = make_product()
        p.delete()
        self.assertTrue(p.is_deleted)
        self.assertIsNotNone(p.deleted_at)
        self.assertFalse(Product.objects.filter(pk=p.pk).exists())
        self.assertTrue(Product.all_objects.filter(pk=p.pk).exists())

    def test_restore(self):
        p = make_product()
        p.delete()
        p.restore()
        self.assertFalse(p.is_deleted)
        self.assertIsNone(p.deleted_at)
        self.assertTrue(Product.objects.filter(pk=p.pk).exists())

    def test_ordering(self):
        self.assertEqual(Product._meta.ordering, ["-created_at"])

    def test_category_protect(self):
        cat = make_category()
        make_product(category=cat)
        with self.assertRaises(Exception):
            cat.delete()


# =============================================================================
# Form Tests — CategoryForm
# =============================================================================

class CategoryFormTest(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "name": "Electronics",
            "slug": "electronics",
            "is_active": True,
            "sort_order": 0,
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = CategoryForm(data=self._valid_data())
        self.assertTrue(form.is_valid())

    def test_valid_minimal(self):
        form = CategoryForm(data=self._valid_data(name="Shoes", slug="shoes"))
        self.assertTrue(form.is_valid())

    def test_slug_optional(self):
        form = CategoryForm(data=self._valid_data(slug=""))
        self.assertTrue(form.is_valid())

    def test_parent_optional(self):
        form = CategoryForm(data=self._valid_data())
        self.assertTrue(form.is_valid())

    def test_missing_name(self):
        form = CategoryForm(data=self._valid_data(name=""))
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_is_active_required(self):
        form = CategoryForm(data={"name": "X", "slug": "x"})
        self.assertFalse(form.is_valid())
        self.assertIn("sort_order", form.errors)


# =============================================================================
# Form Tests — ProductForm
# =============================================================================

class ProductFormTest(TestCase):
    def _valid_data(self, **overrides):
        cat = make_category()
        data = {
            "name": "Widget",
            "slug": "widget",
            "sku": "W001",
            "category": cat.pk,
            "cost_price": "10.00",
            "selling_price": "20.00",
            "stock_quantity": 50,
            "low_stock_threshold": 10,
            "tax_rate": "17.00",
            "is_active": True,
        }
        data.update(overrides)
        return data

    def test_valid_data(self):
        form = ProductForm(data=self._valid_data())
        self.assertTrue(form.is_valid())

    def test_slug_optional(self):
        form = ProductForm(data=self._valid_data(slug=""))
        self.assertTrue(form.is_valid())

    def test_barcode_optional(self):
        form = ProductForm(data=self._valid_data(barcode=""))
        self.assertTrue(form.is_valid())

    def test_image_optional(self):
        form = ProductForm(data=self._valid_data())
        self.assertTrue(form.is_valid())

    def test_missing_required_fields(self):
        form = ProductForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("sku", form.errors)
        self.assertIn("category", form.errors)
        self.assertIn("cost_price", form.errors)
        self.assertIn("selling_price", form.errors)

    def test_category_queryset_active_only(self):
        active = make_category(name="Active", slug="active", is_active=True)
        inactive = make_category(name="Inactive", slug="inactive", is_active=False)
        form = ProductForm()
        self.assertIn(active, form.fields["category"].queryset)
        self.assertNotIn(inactive, form.fields["category"].queryset)


# =============================================================================
# View Tests — Product List
# =============================================================================

class ProductListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.url = reverse("products:product_list")

    def test_empty_list(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_products(self):
        self.client.force_login(self.user)
        make_product()
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["products"]), 1)

    def test_hides_deleted(self):
        self.client.force_login(self.user)
        p = make_product()
        p.delete()
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["products"]), 0)

    def test_search_by_name(self):
        self.client.force_login(self.user)
        make_product(name="Alpha")
        make_product(name="Beta")
        response = self.client.get(self.url, {"search": "Alpha"})
        self.assertEqual(len(response.context["products"]), 1)
        self.assertEqual(response.context["products"][0].name, "Alpha")

    def test_search_by_sku(self):
        self.client.force_login(self.user)
        make_product(sku="ABC123")
        make_product(sku="XYZ789")
        response = self.client.get(self.url, {"search": "ABC"})
        self.assertEqual(len(response.context["products"]), 1)

    def test_search_by_barcode(self):
        self.client.force_login(self.user)
        make_product(barcode="123456789")
        make_product(barcode="987654321")
        response = self.client.get(self.url, {"search": "123456"})
        self.assertEqual(len(response.context["products"]), 1)

    def test_filter_by_category(self):
        self.client.force_login(self.user)
        cat1 = make_category(name="A", slug="a")
        cat2 = make_category(name="B", slug="b")
        make_product(category=cat1)
        make_product(category=cat2)
        response = self.client.get(self.url, {"category": cat1.pk})
        self.assertEqual(len(response.context["products"]), 1)

    def test_filter_status_active(self):
        self.client.force_login(self.user)
        make_product(is_active=True)
        make_product(name="Off", slug="off", sku="OFF", is_active=False)
        response = self.client.get(self.url, {"status": "active"})
        self.assertEqual(len(response.context["products"]), 1)

    def test_filter_status_inactive(self):
        self.client.force_login(self.user)
        make_product(is_active=True)
        make_product(name="Off", slug="off", sku="OFF", is_active=False)
        response = self.client.get(self.url, {"status": "inactive"})
        self.assertEqual(len(response.context["products"]), 1)

    def test_filter_status_low_stock(self):
        self.client.force_login(self.user)
        make_product(stock_quantity=5, low_stock_threshold=10)
        make_product(name="OK", slug="ok", sku="OK01", stock_quantity=50, low_stock_threshold=10)
        response = self.client.get(self.url, {"status": "low_stock"})
        self.assertEqual(len(response.context["products"]), 1)

    def test_filter_status_out_of_stock(self):
        self.client.force_login(self.user)
        make_product(stock_quantity=0)
        make_product(name="Has", slug="has", sku="HAS1", stock_quantity=10)
        response = self.client.get(self.url, {"status": "out_of_stock"})
        self.assertEqual(len(response.context["products"]), 1)

    def test_sort_by_name_asc(self):
        self.client.force_login(self.user)
        make_product(name="Banana", slug="banana", sku="B001")
        make_product(name="Apple", slug="apple", sku="A001")
        response = self.client.get(self.url, {"sort": "name"})
        names = [p.name for p in response.context["products"]]
        self.assertEqual(names, ["Apple", "Banana"])

    def test_sort_by_name_desc(self):
        self.client.force_login(self.user)
        make_product(name="Banana", slug="banana", sku="B001")
        make_product(name="Apple", slug="apple", sku="A001")
        response = self.client.get(self.url, {"sort": "-name"})
        names = [p.name for p in response.context["products"]]
        self.assertEqual(names, ["Banana", "Apple"])

    def test_sort_by_price(self):
        self.client.force_login(self.user)
        make_product(selling_price=Decimal("30.00"))
        make_product(name="Cheap", slug="cheap", sku="C001", selling_price=Decimal("5.00"))
        response = self.client.get(self.url, {"sort": "selling_price"})
        prices = [p.selling_price for p in response.context["products"]]
        self.assertEqual(prices, [Decimal("5.00"), Decimal("30.00")])

    def test_invalid_sort_ignored(self):
        self.client.force_login(self.user)
        make_product()
        response = self.client.get(self.url, {"sort": "evil_field"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["products"]), 1)

    def test_pagination(self):
        self.client.force_login(self.user)
        for i in range(PRODUCTS_PER_PAGE + 5):
            make_product()
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["products"]), PRODUCTS_PER_PAGE)
        response = self.client.get(self.url, {"page": 2})
        self.assertEqual(len(response.context["products"]), 5)


# =============================================================================
# View Tests — Product Create
# =============================================================================

class ProductCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.url = reverse("products:product_create")

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")

    def test_post_creates_product(self):
        self.client.force_login(self.user)
        cat = make_category()
        data = {
            "name": "New Widget", "slug": "new-widget", "sku": "NW001",
            "category": cat.pk, "cost_price": "10.00", "selling_price": "25.00",
            "stock_quantity": 100, "low_stock_threshold": 10, "tax_rate": "17.00",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(sku="NW001").exists())

    def test_post_invalid_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.exists())

    def test_post_redirects_to_list(self):
        self.client.force_login(self.user)
        cat = make_category()
        data = {
            "name": "Widget", "slug": "widget-redirect", "sku": "WR001",
            "category": cat.pk, "cost_price": "5.00", "selling_price": "10.00",
            "stock_quantity": 0, "low_stock_threshold": 5, "tax_rate": "0",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("products:product_list"))

    def test_post_rejects_get(self):
        self.client.force_login(self.user)
        cat = make_category()
        response = self.client.get(self.url, data={"name": "X"})
        self.assertEqual(response.status_code, 200)


# =============================================================================
# View Tests — Product Detail
# =============================================================================

class ProductDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.product = make_product(slug="detail-prod")
        self.url = reverse("products:product_detail", kwargs={"slug": "detail-prod"})

    def test_detail_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["product"], self.product)

    def test_detail_404_for_deleted(self):
        self.client.force_login(self.user)
        self.product.delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_detail_404_for_invalid_slug(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("products:product_detail", kwargs={"slug": "nope"}))
        self.assertEqual(response.status_code, 404)


# =============================================================================
# View Tests — Product Update
# =============================================================================

class ProductUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.product = make_product(slug="upd-prod", name="Old Name")
        self.url = reverse("products:product_update", kwargs={"slug": "upd-prod"})

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Old Name")

    def test_post_updates_product(self):
        self.client.force_login(self.user)
        cat = self.product.category
        data = {
            "name": "New Name", "slug": "upd-prod", "sku": self.product.sku,
            "category": cat.pk, "cost_price": "10.00", "selling_price": "20.00",
            "stock_quantity": 50, "low_stock_threshold": 10, "tax_rate": "0",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "New Name")

    def test_post_invalid_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Old Name")

    def test_post_redirects_to_detail(self):
        self.client.force_login(self.user)
        cat = self.product.category
        data = {
            "name": "Redirected", "slug": "upd-prod", "sku": self.product.sku,
            "category": cat.pk, "cost_price": "10.00", "selling_price": "20.00",
            "stock_quantity": 50, "low_stock_threshold": 10, "tax_rate": "0",
            "is_active": True,
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("products:product_detail", kwargs={"slug": "upd-prod"}))

    def test_update_deleted_product_404(self):
        self.client.force_login(self.user)
        self.product.delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)


# =============================================================================
# View Tests — Product Delete
# =============================================================================

class ProductDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.product = make_product(slug="del-prod")
        self.url = reverse("products:product_delete", kwargs={"slug": "del-prod"})

    def test_post_soft_deletes(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_delete_404_for_already_deleted(self):
        self.client.force_login(self.user)
        self.product.delete()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)

    def test_delete_redirects_to_list(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("products:product_list"))


# =============================================================================
# View Tests — Category List
# =============================================================================

class CategoryListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.url = reverse("products:category_list")

    def test_empty_list(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_root_categories(self):
        self.client.force_login(self.user)
        root = make_category(name="Root")
        make_category(name="Child", parent=root)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["categories"]), 1)
        self.assertEqual(response.context["categories"][0], root)


# =============================================================================
# View Tests — Category Create
# =============================================================================

class CategoryCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.url = reverse("products:category_create")

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")

    def test_post_creates_category(self):
        self.client.force_login(self.user)
        data = {"name": "New Cat", "slug": "new-cat", "is_active": True, "sort_order": 0}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(slug="new-cat").exists())

    def test_post_invalid_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Category.objects.exists())

    def test_post_redirects_to_list(self):
        self.client.force_login(self.user)
        data = {"name": "List Cat", "slug": "list-cat", "is_active": True, "sort_order": 0}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("products:category_list"))


# =============================================================================
# View Tests — Category Update
# =============================================================================

class CategoryUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.category = make_category(slug="upd-cat", name="Old Cat")
        self.url = reverse("products:category_update", kwargs={"slug": "upd-cat"})

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Old Cat")

    def test_post_updates_category(self):
        self.client.force_login(self.user)
        data = {"name": "New Cat", "slug": "upd-cat", "is_active": True, "sort_order": 0}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "New Cat")

    def test_post_invalid_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Old Cat")


# =============================================================================
# View Tests — Category Delete
# =============================================================================

class CategoryDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.category = make_category(slug="del-cat")
        self.url = reverse("products:category_delete", kwargs={"slug": "del-cat"})

    def test_post_deletes(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_redirects_to_list(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("products:category_list"))


# =============================================================================
# Auth Tests
# =============================================================================

class ProductAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="tester", email="t@t.com", password="pass1234"
        )
        self.product = make_product(slug="auth-prod")
        self.category = make_category(slug="auth-cat")

    def test_product_list_requires_login(self):
        response = self.client.get(reverse("products:product_list"))
        self.assertEqual(response.status_code, 302)

    def test_product_create_requires_login(self):
        response = self.client.get(reverse("products:product_create"))
        self.assertEqual(response.status_code, 302)

    def test_product_detail_requires_login(self):
        response = self.client.get(reverse("products:product_detail", kwargs={"slug": "auth-prod"}))
        self.assertEqual(response.status_code, 302)

    def test_product_update_requires_login(self):
        response = self.client.get(reverse("products:product_update", kwargs={"slug": "auth-prod"}))
        self.assertEqual(response.status_code, 302)

    def test_product_delete_requires_login(self):
        response = self.client.post(reverse("products:product_delete", kwargs={"slug": "auth-prod"}))
        self.assertEqual(response.status_code, 302)

    def test_category_list_requires_login(self):
        response = self.client.get(reverse("products:category_list"))
        self.assertEqual(response.status_code, 302)

    def test_category_create_requires_login(self):
        response = self.client.get(reverse("products:category_create"))
        self.assertEqual(response.status_code, 302)

    def test_category_update_requires_login(self):
        response = self.client.get(reverse("products:category_update", kwargs={"slug": "auth-cat"}))
        self.assertEqual(response.status_code, 302)

    def test_category_delete_requires_login(self):
        response = self.client.post(reverse("products:category_delete", kwargs={"slug": "auth-cat"}))
        self.assertEqual(response.status_code, 302)


# =============================================================================
# URL Resolution Tests
# =============================================================================

class ProductURLTest(TestCase):
    def test_product_list(self):
        self.assertEqual(reverse("products:product_list"), "/products/")

    def test_product_create(self):
        self.assertEqual(reverse("products:product_create"), "/products/add/")

    def test_product_detail(self):
        self.assertEqual(reverse("products:product_detail", kwargs={"slug": "x"}), "/products/x/")

    def test_product_update(self):
        self.assertEqual(reverse("products:product_update", kwargs={"slug": "x"}), "/products/x/edit/")

    def test_product_delete(self):
        self.assertEqual(reverse("products:product_delete", kwargs={"slug": "x"}), "/products/x/delete/")

    def test_category_list(self):
        self.assertEqual(reverse("products:category_list"), "/products/categories/")

    def test_category_create(self):
        self.assertEqual(reverse("products:category_create"), "/products/categories/add/")

    def test_category_update(self):
        self.assertEqual(reverse("products:category_update", kwargs={"slug": "x"}), "/products/categories/x/edit/")

    def test_category_delete(self):
        self.assertEqual(reverse("products:category_delete", kwargs={"slug": "x"}), "/products/categories/x/delete/")
