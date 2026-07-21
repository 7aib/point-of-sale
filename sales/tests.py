import json
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from config import ORDERS_PER_PAGE

from customers.models import Customer, Order, OrderItem
from products.models import Product, Category
from discounts.models import Discount, Coupon
from .models import Payment
from .forms import OrderForm, PaymentForm, QuickSaleForm

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
    defaults = {
        "payment_method": Order.PaymentMethod.CASH,
    }
    defaults.update(kwargs)
    order = Order(
        customer=customer,
        performed_by=performed_by,
        **defaults,
    )
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


def make_payment(**kwargs):
    order = kwargs.pop("order", None)
    if order is None:
        order = make_order()
    defaults = {
        "amount": kwargs.pop("amount", order.total_amount or Decimal("20.00")),
        "payment_method": kwargs.pop("payment_method", Payment.PaymentMethod.CASH),
        "status": kwargs.pop("status", Payment.PaymentStatus.COMPLETED),
    }
    return Payment.objects.create(order=order, **defaults)


# =============================================================================
# Model Tests — Payment
# =============================================================================

class PaymentModelTest(TestCase):
    def test_str(self):
        order = make_order()
        order.save()
        p = make_payment(order=order, amount=Decimal("50.00"))
        self.assertIn(str(order.pk), str(p))
        self.assertIn("50.00", str(p))

    def test_str_contains_order_number(self):
        order = make_order()
        p = make_payment(order=order)
        self.assertIn(order.order_number, str(p))

    def test_choices(self):
        self.assertEqual(Payment.PaymentMethod.CASH, "cash")
        self.assertEqual(Payment.PaymentStatus.COMPLETED, "completed")

    def test_ordering(self):
        self.assertEqual(Payment._meta.ordering, ["-created_at"])

    def test_save_updates_order_to_completed(self):
        order = make_order()
        make_payment(order=order, amount=Decimal("20.00"), status=Payment.PaymentStatus.COMPLETED)
        order.refresh_from_db()
        self.assertEqual(order.status, "completed")

    def test_save_updates_order_to_pending(self):
        order = make_order()
        make_order_item(order=order, quantity=5, unit_price=Decimal("10.00"))
        order.subtotal = Decimal("50.00")
        order.total_amount = Decimal("50.00")
        order.save(update_fields=["subtotal", "total_amount"])
        make_payment(order=order, amount=Decimal("10.00"), status=Payment.PaymentStatus.COMPLETED)
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_save_no_change_for_failed_payment(self):
        order = make_order()
        make_order_item(order=order, quantity=5, unit_price=Decimal("10.00"))
        order.subtotal = Decimal("50.00")
        order.total_amount = Decimal("50.00")
        order.save(update_fields=["subtotal", "total_amount"])
        order.status = "pending"
        order.save(update_fields=["status"])
        make_payment(order=order, amount=Decimal("10.00"), status=Payment.PaymentStatus.FAILED)
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")


# =============================================================================
# Form Tests
# =============================================================================

class OrderFormTest(TestCase):
    def test_valid_data(self):
        customer = make_customer()
        form = OrderForm(data={
            "customer": customer.pk,
            "payment_method": "cash",
            "status": "completed",
            "notes": "",
        })
        self.assertTrue(form.is_valid())

    def test_customer_queryset_excludes_deleted(self):
        active = make_customer(first_name="Active")
        deleted = make_customer(first_name="Deleted", is_deleted=True)
        form = OrderForm()
        self.assertIn(active, form.fields["customer"].queryset)
        self.assertNotIn(deleted, form.fields["customer"].queryset)


class PaymentFormTest(TestCase):
    def test_valid_data(self):
        form = PaymentForm(data={
            "amount": "50.00",
            "payment_method": "cash",
            "transaction_id": "",
            "notes": "",
        })
        self.assertTrue(form.is_valid())

    def test_missing_required(self):
        form = PaymentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("amount", form.errors)


class QuickSaleFormTest(TestCase):
    def test_valid_empty(self):
        form = QuickSaleForm(data={
            "payment_method": "cash",
        })
        self.assertTrue(form.is_valid())

    def test_customer_queryset_excludes_deleted(self):
        active = make_customer(first_name="A")
        deleted = make_customer(first_name="D", is_deleted=True)
        form = QuickSaleForm()
        self.assertIn(active, form.fields["customer"].queryset)
        self.assertNotIn(deleted, form.fields["customer"].queryset)


# =============================================================================
# View Tests — Dashboard
# =============================================================================

class DashboardViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("sales:dashboard")

    def test_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_empty_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["today_count"], 0)
        self.assertEqual(response.context["total_orders"], 0)

    def test_shows_stats(self):
        self.client.force_login(self.user)
        make_order()
        make_order()
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_orders"], 2)

    def test_excludes_refunded_from_revenue(self):
        self.client.force_login(self.user)
        order1 = make_order()
        make_order_item(order=order1, quantity=2, unit_price=Decimal("25.00"))
        order1.subtotal = Decimal("50.00")
        order1.total_amount = Decimal("50.00")
        order1.save(update_fields=["subtotal", "total_amount"])
        order2 = make_order()
        make_order_item(order=order2, quantity=1, unit_price=Decimal("50.00"))
        order2.subtotal = Decimal("50.00")
        order2.total_amount = Decimal("50.00")
        order2.save(update_fields=["subtotal", "total_amount"])
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_revenue"], Decimal("100.00"))
        order2.status = "refunded"
        order2.save(update_fields=["status"])
        response = self.client.get(self.url)
        self.assertEqual(response.context["total_revenue"], Decimal("50.00"))
        self.assertEqual(response.context["total_orders"], 1)


# =============================================================================
# View Tests — Order List
# =============================================================================

class OrderListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("sales:order_list")

    def test_empty_list(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_orders(self):
        self.client.force_login(self.user)
        make_order()
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["orders"]), 1)

    def test_search_by_order_number(self):
        self.client.force_login(self.user)
        o1 = make_order()
        o2 = make_order()
        response = self.client.get(self.url, {"search": o1.order_number})
        self.assertEqual(len(response.context["orders"]), 1)

    def test_search_by_customer_name(self):
        self.client.force_login(self.user)
        c = make_customer(first_name="Alice", last_name="Smith")
        make_order(customer=c)
        make_order()
        response = self.client.get(self.url, {"search": "Alice"})
        self.assertEqual(len(response.context["orders"]), 1)

    def test_filter_by_status(self):
        self.client.force_login(self.user)
        make_order(status="pending")
        make_order(status="completed")
        response = self.client.get(self.url, {"status": "pending"})
        self.assertEqual(len(response.context["orders"]), 1)

    def test_filter_by_payment_method(self):
        self.client.force_login(self.user)
        make_order(payment_method="cash")
        make_order(payment_method="card")
        response = self.client.get(self.url, {"payment_method": "card"})
        self.assertEqual(len(response.context["orders"]), 1)

    def test_date_from_filter(self):
        self.client.force_login(self.user)
        make_order()
        response = self.client.get(self.url, {"date_from": "2020-01-01"})
        self.assertEqual(len(response.context["orders"]), 1)
        response = self.client.get(self.url, {"date_from": "2099-01-01"})
        self.assertEqual(len(response.context["orders"]), 0)

    def test_date_to_filter(self):
        self.client.force_login(self.user)
        make_order()
        response = self.client.get(self.url, {"date_to": "2099-12-31"})
        self.assertEqual(len(response.context["orders"]), 1)
        response = self.client.get(self.url, {"date_to": "2020-01-01"})
        self.assertEqual(len(response.context["orders"]), 0)

    def test_sort_by_order_number(self):
        self.client.force_login(self.user)
        o1 = make_order()
        o2 = make_order()
        response = self.client.get(self.url, {"sort": "order_number"})
        orders = list(response.context["orders"])
        self.assertEqual(orders[0], o1)

    def test_invalid_sort_ignored(self):
        self.client.force_login(self.user)
        make_order()
        response = self.client.get(self.url, {"sort": "evil"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["orders"]), 1)

    def test_pagination(self):
        self.client.force_login(self.user)
        for _ in range(ORDERS_PER_PAGE + 5):
            make_order()
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["orders"]), ORDERS_PER_PAGE)
        response = self.client.get(self.url, {"page": 2})
        self.assertEqual(len(response.context["orders"]), 5)


# =============================================================================
# View Tests — Order Create
# =============================================================================

class OrderCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("sales:order_create")

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "form")

    def test_post_creates_order(self):
        self.client.force_login(self.user)
        customer = make_customer()
        product = make_product()
        data = {
            "customer": customer.pk,
            "payment_method": "cash",
            "status": "completed",
            "notes": "",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-0-product": product.pk,
            "items-0-quantity": "2",
            "items-0-unit_price": "",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.exists())

    def test_post_creates_order_item(self):
        self.client.force_login(self.user)
        customer = make_customer()
        product = make_product(selling_price=Decimal("25.00"))
        data = {
            "customer": customer.pk,
            "payment_method": "card",
            "status": "pending",
            "notes": "test",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-0-product": product.pk,
            "items-0-quantity": "3",
            "items-0-unit_price": "",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.first()
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.unit_price, Decimal("25.00"))

    def test_post_sets_performed_by(self):
        self.client.force_login(self.user)
        customer = make_customer()
        product = make_product()
        data = {
            "customer": customer.pk,
            "payment_method": "cash",
            "status": "completed",
            "notes": "",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-0-product": product.pk,
            "items-0-quantity": "1",
            "items-0-unit_price": "",
        }
        self.client.post(self.url, data)
        order = Order.objects.first()
        self.assertEqual(order.performed_by, self.user)

    def test_post_invalid_returns_form(self):
        self.client.force_login(self.user)
        data = {
            "customer": "",
            "payment_method": "cash",
            "status": "completed",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "1",
            "items-0-product": "",
            "items-0-quantity": "1",
            "items-0-unit_price": "",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())


# =============================================================================
# View Tests — Order Detail
# =============================================================================

class OrderDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.order = make_order()
        self.url = reverse("sales:order_detail", kwargs={"pk": self.order.pk})

    def test_detail_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["order"], self.order)

    def test_detail_shows_payments(self):
        self.client.force_login(self.user)
        make_payment(order=self.order)
        response = self.client.get(self.url)
        self.assertEqual(response.context["payments"].count(), 1)

    def test_detail_calculates_balance(self):
        self.client.force_login(self.user)
        order = make_order()
        make_order_item(order=order, quantity=2, unit_price=Decimal("10.00"))
        order.refresh_from_db()
        make_payment(order=order, amount=Decimal("10.00"))
        response = self.client.get(reverse("sales:order_detail", kwargs={"pk": order.pk}))
        self.assertEqual(response.context["total_paid"], Decimal("10.00"))

    def test_detail_404(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("sales:order_detail", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)


# =============================================================================
# View Tests — Order Update
# =============================================================================

class OrderUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.order = make_order()
        self.item = make_order_item(order=self.order)
        self.url = reverse("sales:order_update", kwargs={"pk": self.order.pk})

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_updates_order(self):
        self.client.force_login(self.user)
        data = {
            "customer": self.order.customer.pk,
            "payment_method": "card",
            "status": "pending",
            "notes": "updated",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "1",
            "items-MIN_NUM_FORMS": "1",
            "items-0-id": self.item.pk,
            "items-0-product": self.item.product.pk,
            "items-0-quantity": self.item.quantity,
            "items-0-unit_price": str(self.item.unit_price),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.notes, "updated")


# =============================================================================
# View Tests — Order Delete
# =============================================================================

class OrderDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.order = make_order()
        self.url = reverse("sales:order_delete", kwargs={"pk": self.order.pk})

    def test_post_soft_deletes(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_deleted)
        self.assertIsNotNone(self.order.deleted_at)

    def test_post_soft_deletes_with_payments(self):
        self.client.force_login(self.user)
        make_payment(order=self.order)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_deleted)

    def test_deleted_order_hidden_from_list(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        response = self.client.get(reverse("sales:order_list"))
        self.assertEqual(len(response.context["orders"]), 0)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_redirects_to_list(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("sales:order_list"))


# =============================================================================
# View Tests — Order Status Update
# =============================================================================

class OrderStatusUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.order = make_order()
        self.url = reverse("sales:order_status_update", kwargs={"pk": self.order.pk})

    def test_post_valid_status(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"status": "pending"})
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_post_invalid_status(self):
        self.client.force_login(self.user)
        original = self.order.status
        response = self.client.post(self.url, {"status": "bogus"})
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, original)

    def test_post_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


# =============================================================================
# View Tests — Payment Create
# =============================================================================

class PaymentCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.order = make_order()
        self.url = reverse("sales:payment_create", kwargs={"order_pk": self.order.pk})

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_post_creates_payment(self):
        self.client.force_login(self.user)
        data = {
            "amount": "20.00",
            "payment_method": "cash",
            "transaction_id": "",
            "notes": "",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payment.objects.filter(order=self.order).exists())

    def test_post_sets_received_by(self):
        self.client.force_login(self.user)
        data = {"amount": "20.00", "payment_method": "cash"}
        self.client.post(self.url, data)
        payment = Payment.objects.first()
        self.assertEqual(payment.received_by, self.user)

    def test_post_invalid_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Payment.objects.exists())


# =============================================================================
# View Tests — Payment Refund
# =============================================================================

class PaymentRefundViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.order = make_order()
        self.product = make_product(stock_quantity=100)
        self.item = make_order_item(order=self.order, product=self.product, quantity=3)
        self.order.subtotal = self.item.total_price
        self.order.total_amount = self.item.total_price
        self.order.save(update_fields=["subtotal", "total_amount"])
        self.payment = make_payment(order=self.order, amount=self.order.total_amount)
        self.url = reverse("sales:payment_refund", kwargs={"pk": self.payment.pk})

    def test_post_refunds_completed_payment(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.REFUNDED)

    def test_post_sets_order_status_refunded(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "refunded")

    def test_post_restores_stock(self):
        self.client.force_login(self.user)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 100)
        response = self.client.post(self.url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 103)

    def test_post_creates_stock_movement(self):
        self.client.force_login(self.user)
        from inventory.models import StockMovement
        response = self.client.post(self.url)
        movement = StockMovement.objects.filter(
            product=self.product,
            reference=self.order.order_number,
            movement_type="in",
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, 3)

    def test_post_rejects_non_completed(self):
        self.client.force_login(self.user)
        self.payment.status = Payment.PaymentStatus.FAILED
        self.payment.save(update_fields=["status"])
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.FAILED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 100)

    def test_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


# =============================================================================
# View Tests — Quick Sale
# =============================================================================

class QuickSaleViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("sales:quick_sale")
        self.product = make_product(selling_price=Decimal("25.00"), stock_quantity=100)
        self.customer = make_customer(first_name="Walk-in")

    def test_get_returns_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_creates_order(self):
        self.client.force_login(self.user)
        data = {
            "payment_method": "cash",
            "item_product[]": [str(self.product.pk)],
            "item_quantity[]": ["2"],
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.exists())

    def test_post_creates_order_item(self):
        self.client.force_login(self.user)
        data = {
            "payment_method": "cash",
            "item_product[]": [str(self.product.pk)],
            "item_quantity[]": ["3"],
        }
        self.client.post(self.url, data)
        order = Order.objects.first()
        self.assertEqual(order.items.count(), 1)
        item = order.items.first()
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.unit_price, Decimal("25.00"))

    def test_post_creates_payment(self):
        self.client.force_login(self.user)
        data = {
            "payment_method": "cash",
            "item_product[]": [str(self.product.pk)],
            "item_quantity[]": ["1"],
        }
        self.client.post(self.url, data)
        order = Order.objects.first()
        self.assertEqual(order.payments.count(), 1)

    def test_post_with_discount_code(self):
        self.client.force_login(self.user)
        discount = Discount.objects.create(
            name="Test Discount", code="SAVE10",
            discount_type="percentage", value=Decimal("10.00"),
            is_active=True,
        )
        data = {
            "payment_method": "cash",
            "discount_code": "SAVE10",
            "item_product[]": [str(self.product.pk)],
            "item_quantity[]": ["1"],
        }
        self.client.post(self.url, data)
        order = Order.objects.first()
        self.assertTrue(order.discount_amount > 0)
        discount.refresh_from_db()
        self.assertEqual(discount.used_count, 1)

    def test_post_empty_items_redirects(self):
        self.client.force_login(self.user)
        data = {"payment_method": "cash", "item_product[]": [], "item_quantity[]": []}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Order.objects.exists())

    def test_post_walkin_customer(self):
        self.client.force_login(self.user)
        data = {
            "payment_method": "cash",
            "item_product[]": [str(self.product.pk)],
            "item_quantity[]": ["1"],
        }
        self.client.post(self.url, data)
        order = Order.objects.first()
        self.assertEqual(order.customer.first_name, "Walk-in")


# =============================================================================
# View Tests — POS Terminal
# =============================================================================

class POSTerminalViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("sales:pos_terminal")

    def test_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_products(self):
        self.client.force_login(self.user)
        make_product()
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["products"]), 1)

    def test_excludes_zero_stock(self):
        self.client.force_login(self.user)
        make_product(stock_quantity=0)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["products"]), 0)


# =============================================================================
# View Tests — Barcode Lookup
# =============================================================================

class BarcodeLookupViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("sales:barcode_lookup")
        self.product = make_product(barcode="5901234123457")

    def test_found_by_barcode(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"code": "5901234123457"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["name"], self.product.name)

    def test_found_by_sku(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"code": self.product.sku})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["sku"], self.product.sku)

    def test_not_found(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"code": "NONEXISTENT"})
        self.assertEqual(response.status_code, 404)

    def test_empty_code(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"code": ""})
        self.assertEqual(response.status_code, 400)

    def test_no_code_param(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)


# =============================================================================
# View Tests — POS Create Order
# =============================================================================

class POSCreateOrderViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.url = reverse("sales:pos_create_order")
        self.product = make_product(selling_price=Decimal("30.00"), stock_quantity=100)

    def _post(self, data):
        return self.client.post(
            self.url,
            json.dumps(data),
            content_type="application/json",
        )

    def test_create_order(self):
        self.client.force_login(self.user)
        response = self._post({
            "items": [{"id": self.product.pk, "quantity": 2}],
            "payment_method": "cash",
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertTrue(Order.objects.exists())

    def test_create_order_deducts_stock(self):
        self.client.force_login(self.user)
        self._post({"items": [{"id": self.product.pk, "quantity": 3}], "payment_method": "cash"})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 97)

    def test_create_order_with_payment(self):
        self.client.force_login(self.user)
        self._post({"items": [{"id": self.product.pk, "quantity": 1}], "payment_method": "card"})
        order = Order.objects.first()
        self.assertEqual(order.payments.count(), 1)

    def test_no_items(self):
        self.client.force_login(self.user)
        response = self._post({"items": [], "payment_method": "cash"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_json(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, "not json", content_type="text/plain")
        self.assertEqual(response.status_code, 400)

    def test_with_discount_code(self):
        self.client.force_login(self.user)
        Discount.objects.create(
            name="Off", code="OFF20", discount_type="percentage",
            value=Decimal("20.00"), is_active=True,
        )
        response = self._post({
            "items": [{"id": self.product.pk, "quantity": 1}],
            "discount_code": "OFF20",
            "payment_method": "cash",
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(Decimal(data["discount"]) > 0)

    def test_with_customer_id(self):
        self.client.force_login(self.user)
        customer = make_customer()
        self._post({
            "items": [{"id": self.product.pk, "quantity": 1}],
            "customer_id": customer.pk,
            "payment_method": "cash",
        })
        order = Order.objects.first()
        self.assertEqual(order.customer, customer)


# =============================================================================
# Auth Tests
# =============================================================================

class SalesAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.order = make_order()
        self.payment = make_payment(order=self.order)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("sales:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_order_list_requires_login(self):
        response = self.client.get(reverse("sales:order_list"))
        self.assertEqual(response.status_code, 302)

    def test_order_create_requires_login(self):
        response = self.client.get(reverse("sales:order_create"))
        self.assertEqual(response.status_code, 302)

    def test_order_detail_requires_login(self):
        response = self.client.get(reverse("sales:order_detail", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, 302)

    def test_order_update_requires_login(self):
        response = self.client.get(reverse("sales:order_update", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, 302)

    def test_order_delete_requires_login(self):
        response = self.client.post(reverse("sales:order_delete", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, 302)

    def test_order_status_requires_login(self):
        response = self.client.post(reverse("sales:order_status_update", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, 302)

    def test_payment_create_requires_login(self):
        response = self.client.get(reverse("sales:payment_create", kwargs={"order_pk": self.order.pk}))
        self.assertEqual(response.status_code, 302)

    def test_payment_refund_requires_login(self):
        response = self.client.post(reverse("sales:payment_refund", kwargs={"pk": self.payment.pk}))
        self.assertEqual(response.status_code, 302)

    def test_quick_sale_requires_login(self):
        response = self.client.get(reverse("sales:quick_sale"))
        self.assertEqual(response.status_code, 302)

    def test_pos_terminal_requires_login(self):
        response = self.client.get(reverse("sales:pos_terminal"))
        self.assertEqual(response.status_code, 302)

    def test_barcode_lookup_requires_login(self):
        response = self.client.get(reverse("sales:barcode_lookup"))
        self.assertEqual(response.status_code, 302)

    def test_pos_create_order_requires_login(self):
        response = self.client.post(
            reverse("sales:pos_create_order"),
            json.dumps({"items": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)


# =============================================================================
# URL Resolution Tests
# =============================================================================

class SalesURLTest(TestCase):
    def test_dashboard(self):
        self.assertEqual(reverse("sales:dashboard"), "/sales/")

    def test_pos_terminal(self):
        self.assertEqual(reverse("sales:pos_terminal"), "/sales/terminal/")

    def test_barcode_lookup(self):
        self.assertEqual(reverse("sales:barcode_lookup"), "/sales/api/barcode/")

    def test_pos_create_order(self):
        self.assertEqual(reverse("sales:pos_create_order"), "/sales/api/create-order/")

    def test_order_list(self):
        self.assertEqual(reverse("sales:order_list"), "/sales/orders/")

    def test_order_create(self):
        self.assertEqual(reverse("sales:order_create"), "/sales/orders/create/")

    def test_order_detail(self):
        self.assertEqual(reverse("sales:order_detail", kwargs={"pk": 1}), "/sales/orders/1/")

    def test_order_update(self):
        self.assertEqual(reverse("sales:order_update", kwargs={"pk": 1}), "/sales/orders/1/edit/")

    def test_order_delete(self):
        self.assertEqual(reverse("sales:order_delete", kwargs={"pk": 1}), "/sales/orders/1/delete/")

    def test_order_status_update(self):
        self.assertEqual(reverse("sales:order_status_update", kwargs={"pk": 1}), "/sales/orders/1/status/")

    def test_payment_create(self):
        self.assertEqual(reverse("sales:payment_create", kwargs={"order_pk": 1}), "/sales/orders/1/pay/")

    def test_payment_refund(self):
        self.assertEqual(reverse("sales:payment_refund", kwargs={"pk": 1}), "/sales/payments/1/refund/")

    def test_quick_sale(self):
        self.assertEqual(reverse("sales:quick_sale"), "/sales/quick-sale/")
