import json
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from customers.models import Customer, Order, OrderItem
from products.models import Product, Category
from sales.models import Payment

User = get_user_model()


# =============================================================================
# Factories
# =============================================================================

_user_counter = 0


def make_user(**kwargs):
    global _user_counter
    _user_counter += 1
    defaults = {
        "username": f"user{_user_counter}",
        "email": f"u{_user_counter}@t.com",
        "password": "pass1234",
    }
    defaults.update(kwargs)
    password = defaults.pop("password")
    return User.objects.create_user(**defaults, password=password)


_customer_counter = 0


def make_customer(**kwargs):
    global _customer_counter
    _customer_counter += 1
    defaults = {
        "first_name": f"Cust{_customer_counter}",
        "last_name": "",
    }
    defaults.update(kwargs)
    return Customer.objects.create(**defaults)


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


def make_order(**kwargs):
    customer = kwargs.pop("customer", None)
    if customer is None:
        customer = make_customer()
    performed_by = kwargs.pop("performed_by", None)
    if performed_by is None:
        performed_by = make_user()
    defaults = {"payment_method": "cash", "status": "completed"}
    defaults.update(kwargs)
    order = Order(customer=customer, performed_by=performed_by, **defaults)
    order.save()
    return order


def make_order_item(**kwargs):
    order = kwargs.pop("order", None)
    product = kwargs.pop("product", None)
    if product is None:
        product = make_product()
    if order is None:
        order = make_order()
    defaults = {
        "quantity": kwargs.pop("quantity", 1),
        "unit_price": kwargs.pop("unit_price", product.selling_price),
    }
    item = OrderItem(order=order, product=product, **defaults)
    item.save()
    return item


def make_completed_order_with_item(**kwargs):
    """Create a completed order with one item and set totals."""
    item_kwargs = {}
    order_kwargs = {}
    for k, v in kwargs.items():
        if k in ("quantity", "unit_price", "product"):
            item_kwargs[k] = v
        else:
            order_kwargs[k] = v
    order_kwargs.setdefault("status", "completed")
    order = make_order(**order_kwargs)
    item = make_order_item(order=order, **item_kwargs)
    order.subtotal = item.total_price
    order.total_amount = item.total_price
    order.save(update_fields=["subtotal", "total_amount"])
    return order, item


# =============================================================================
# View Tests — Reports Dashboard
# =============================================================================

class ReportsDashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:dashboard")

    def test_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_empty_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_orders"], 0)
        self.assertEqual(response.context["total_customers"], 0)
        self.assertEqual(response.context["total_products"], 0)

    def test_shows_completed_orders(self):
        self.client.force_login(self.user)
        make_order(status="completed")
        make_order(status="cancelled")
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_orders"], 1)

    def test_shows_revenue(self):
        self.client.force_login(self.user)
        make_completed_order_with_item(quantity=2, unit_price=Decimal("25.00"))
        response = self.client.get(self.url)
        self.assertTrue(response.context["total_revenue"] > 0)

    def test_counts_customers_and_products(self):
        self.client.force_login(self.user)
        make_customer()
        make_customer()
        make_product()
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_customers"], 2)
        self.assertEqual(response.context["total_products"], 1)

    def test_low_stock_count(self):
        self.client.force_login(self.user)
        make_product(stock_quantity=2, low_stock_threshold=10)
        make_product(stock_quantity=50)
        response = self.client.get(self.url)
        self.assertEqual(response.context["low_stock"], 1)


# =============================================================================
# View Tests — Sales Report
# =============================================================================

class SalesReportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:sales_report")

    def test_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_default_date_range(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn("date_from", response.context)
        self.assertIn("date_to", response.context)

    def test_custom_date_range(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"date_from": "2025-01-01", "date_to": "2025-12-31"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["date_from"], "2025-01-01")

    def test_invalid_date_range(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"date_from": "not-a-date", "date_to": "also-not"})
        self.assertEqual(response.status_code, 200)

    def test_counts_orders(self):
        self.client.force_login(self.user)
        make_order(status="completed")
        make_order(status="cancelled")
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_orders"], 2)
        self.assertEqual(response.context["completed_orders"], 1)
        self.assertEqual(response.context["cancelled_orders"], 1)

    def test_revenue_only_completed(self):
        self.client.force_login(self.user)
        make_completed_order_with_item(quantity=1, unit_price=Decimal("50.00"))
        make_order(status="pending")
        response = self.client.get(self.url)
        self.assertTrue(response.context["total_revenue"] > 0)

    def test_top_products(self):
        self.client.force_login(self.user)
        cat = make_category(name="Electronics", slug="electronics")
        p1 = make_product(name="Laptop", slug="laptop", sku="LAP01", category=cat)
        p2 = make_product(name="Mouse", slug="mouse", sku="MOU01", category=cat)
        make_completed_order_with_item(product=p1, quantity=5, unit_price=Decimal("100.00"))
        make_completed_order_with_item(product=p2, quantity=2, unit_price=Decimal("20.00"))
        response = self.client.get(self.url)
        top = list(response.context["top_products"])
        self.assertTrue(len(top) >= 2)

    def test_top_categories(self):
        self.client.force_login(self.user)
        cat = make_category(name="Food", slug="food")
        p = make_product(name="Fruit", slug="fruit", sku="FRU01", category=cat)
        make_completed_order_with_item(product=p, quantity=3, unit_price=Decimal("10.00"))
        response = self.client.get(self.url)
        self.assertIsNotNone(response.context["top_categories"])

    def test_payment_methods(self):
        self.client.force_login(self.user)
        make_order(payment_method="cash", status="completed")
        make_order(payment_method="card", status="completed")
        response = self.client.get(self.url)
        self.assertEqual(response.context["payment_methods"].count(), 2)

    def test_daily_revenue(self):
        self.client.force_login(self.user)
        make_completed_order_with_item()
        response = self.client.get(self.url)
        self.assertIsInstance(response.context["daily_revenue"], list)

    def test_hourly_orders(self):
        self.client.force_login(self.user)
        make_completed_order_with_item()
        response = self.client.get(self.url)
        self.assertIsInstance(response.context["hourly_orders"], list)


# =============================================================================
# View Tests — Product Report
# =============================================================================

class ProductReportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:product_report")

    def test_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_products(self):
        self.client.force_login(self.user)
        make_product()
        response = self.client.get(self.url)
        self.assertTrue(len(response.context["products"]) >= 1)

    def test_shows_low_stock(self):
        self.client.force_login(self.user)
        make_product(stock_quantity=2, low_stock_threshold=10)
        make_product(stock_quantity=50)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["low_stock_products"]), 1)

    def test_date_filter(self):
        self.client.force_login(self.user)
        make_completed_order_with_item()
        response = self.client.get(self.url, {
            "date_from": "2020-01-01",
            "date_to": "2099-12-31",
        })
        self.assertEqual(response.status_code, 200)

    def test_shows_categories(self):
        self.client.force_login(self.user)
        make_category(name="Books", slug="books")
        response = self.client.get(self.url)
        self.assertTrue(len(response.context["categories"]) >= 1)


# =============================================================================
# View Tests — Customer Report
# =============================================================================

class CustomerReportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:customer_report")

    def test_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_customers_with_orders(self):
        self.client.force_login(self.user)
        c = make_customer()
        make_order(customer=c)
        response = self.client.get(self.url)
        self.assertTrue(len(response.context["top_customers"]) >= 1)

    def test_excludes_customers_without_orders(self):
        self.client.force_login(self.user)
        make_customer()
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["top_customers"]), 0)

    def test_total_customers_count(self):
        self.client.force_login(self.user)
        make_customer()
        make_customer()
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_customers"], 2)

    def test_customers_with_orders_count(self):
        self.client.force_login(self.user)
        c = make_customer()
        make_order(customer=c)
        make_customer()
        response = self.client.get(self.url)
        self.assertEqual(response.context["customers_with_orders"], 1)

    def test_customer_acquisition(self):
        self.client.force_login(self.user)
        make_customer()
        response = self.client.get(self.url)
        self.assertIsInstance(response.context["customer_acquisition"], list)

    def test_date_filter(self):
        self.client.force_login(self.user)
        c = make_customer()
        make_order(customer=c)
        response = self.client.get(self.url, {
            "date_from": "2020-01-01",
            "date_to": "2099-12-31",
        })
        self.assertEqual(response.status_code, 200)


# =============================================================================
# View Tests — Chart: Daily Revenue
# =============================================================================

class ChartDailyRevenueTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:chart_daily_revenue")

    def test_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("labels", data)
        self.assertIn("revenue", data)
        self.assertIn("orders", data)

    def test_empty_data(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(data["labels"], [])

    def test_with_data(self):
        self.client.force_login(self.user)
        make_completed_order_with_item(quantity=2, unit_price=Decimal("30.00"))
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertTrue(len(data["labels"]) >= 1)

    def test_custom_days(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"days": 7})
        self.assertEqual(response.status_code, 200)


# =============================================================================
# View Tests — Chart: Payment Methods
# =============================================================================

class ChartPaymentMethodsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:chart_payment_methods")

    def test_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("labels", data)
        self.assertIn("values", data)
        self.assertIn("counts", data)

    def test_with_data(self):
        self.client.force_login(self.user)
        make_order(payment_method="cash", status="completed")
        make_order(payment_method="card", status="completed")
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(len(data["labels"]), 2)


# =============================================================================
# View Tests — Chart: Top Products
# =============================================================================

class ChartTopProductsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:chart_top_products")

    def test_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("labels", data)
        self.assertIn("quantity", data)
        self.assertIn("revenue", data)

    def test_with_data(self):
        self.client.force_login(self.user)
        p = make_product(name="Best Seller")
        make_completed_order_with_item(product=p, quantity=10)
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertTrue(len(data["labels"]) >= 1)


# =============================================================================
# View Tests — Chart: Category Revenue
# =============================================================================

class ChartCategoryRevenueTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:chart_category_revenue")

    def test_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("labels", data)
        self.assertIn("values", data)


# =============================================================================
# View Tests — Chart: Order Status
# =============================================================================

class ChartOrderStatusTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:chart_order_status")

    def test_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("labels", data)
        self.assertIn("values", data)
        self.assertIn("colors", data)

    def test_with_data(self):
        self.client.force_login(self.user)
        make_order(status="completed")
        make_order(status="pending")
        response = self.client.get(self.url)
        data = json.loads(response.content)
        self.assertEqual(len(data["labels"]), 2)


# =============================================================================
# View Tests — Chart: Hourly Orders
# =============================================================================

class ChartHourlyOrdersTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("reports:chart_hourly_orders")

    def test_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("labels", data)
        self.assertIn("counts", data)
        self.assertIn("revenue", data)


# =============================================================================
# Auth Tests
# =============================================================================

class ReportsAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("reports:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_sales_report_requires_login(self):
        response = self.client.get(reverse("reports:sales_report"))
        self.assertEqual(response.status_code, 302)

    def test_product_report_requires_login(self):
        response = self.client.get(reverse("reports:product_report"))
        self.assertEqual(response.status_code, 302)

    def test_customer_report_requires_login(self):
        response = self.client.get(reverse("reports:customer_report"))
        self.assertEqual(response.status_code, 302)

    def test_chart_daily_revenue_requires_login(self):
        response = self.client.get(reverse("reports:chart_daily_revenue"))
        self.assertEqual(response.status_code, 302)

    def test_chart_payment_methods_requires_login(self):
        response = self.client.get(reverse("reports:chart_payment_methods"))
        self.assertEqual(response.status_code, 302)

    def test_chart_top_products_requires_login(self):
        response = self.client.get(reverse("reports:chart_top_products"))
        self.assertEqual(response.status_code, 302)

    def test_chart_category_revenue_requires_login(self):
        response = self.client.get(reverse("reports:chart_category_revenue"))
        self.assertEqual(response.status_code, 302)

    def test_chart_order_status_requires_login(self):
        response = self.client.get(reverse("reports:chart_order_status"))
        self.assertEqual(response.status_code, 302)

    def test_chart_hourly_orders_requires_login(self):
        response = self.client.get(reverse("reports:chart_hourly_orders"))
        self.assertEqual(response.status_code, 302)


# =============================================================================
# URL Resolution Tests
# =============================================================================

class ReportsURLTest(TestCase):
    def test_dashboard(self):
        self.assertEqual(reverse("reports:dashboard"), "/reports/")

    def test_sales_report(self):
        self.assertEqual(reverse("reports:sales_report"), "/reports/sales/")

    def test_product_report(self):
        self.assertEqual(reverse("reports:product_report"), "/reports/products/")

    def test_customer_report(self):
        self.assertEqual(reverse("reports:customer_report"), "/reports/customers/")

    def test_chart_daily_revenue(self):
        self.assertEqual(reverse("reports:chart_daily_revenue"), "/reports/api/daily-revenue/")

    def test_chart_payment_methods(self):
        self.assertEqual(reverse("reports:chart_payment_methods"), "/reports/api/payment-methods/")

    def test_chart_top_products(self):
        self.assertEqual(reverse("reports:chart_top_products"), "/reports/api/top-products/")

    def test_chart_category_revenue(self):
        self.assertEqual(reverse("reports:chart_category_revenue"), "/reports/api/category-revenue/")

    def test_chart_order_status(self):
        self.assertEqual(reverse("reports:chart_order_status"), "/reports/api/order-status/")

    def test_chart_hourly_orders(self):
        self.assertEqual(reverse("reports:chart_hourly_orders"), "/reports/api/hourly-orders/")
