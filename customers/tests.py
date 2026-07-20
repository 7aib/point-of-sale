from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Customer, Order, OrderItem
from .forms import CustomerForm
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


# =============================================================================
# Model Tests - Customer
# =============================================================================

class CustomerModelTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Ali",
            last_name="Khan",
            email="ali@example.com",
            phone="+923011234567",
            address="123 Main St",
            city="Lahore",
        )

    def test_str(self):
        self.assertEqual(str(self.customer), "Ali Khan")

    def test_str_no_last_name(self):
        c = Customer.objects.create(first_name="Sara", last_name="")
        self.assertEqual(str(c), "Sara")

    def test_full_name(self):
        self.assertEqual(self.customer.full_name, "Ali Khan")

    def test_full_name_no_last(self):
        c = Customer.objects.create(first_name="Sara")
        self.assertEqual(c.full_name, "Sara")

    def test_soft_delete(self):
        self.customer.delete()
        self.assertTrue(self.customer.is_deleted)
        self.assertIsNotNone(self.customer.deleted_at)
        self.assertNotIn(self.customer, Customer.objects.all())

    def test_soft_delete_queryset(self):
        Customer.objects.create(first_name="Deleted")
        deleted = Customer.objects.first()
        deleted.delete()
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Customer.all_objects.count(), 2)

    def test_restore(self):
        self.customer.delete()
        self.customer.restore()
        self.assertFalse(self.customer.is_deleted)
        self.assertIsNone(self.customer.deleted_at)
        self.assertEqual(Customer.objects.count(), 1)

    def test_total_orders_no_orders(self):
        self.assertEqual(self.customer.total_orders, 0)

    def test_total_orders_with_orders(self):
        product = make_product()
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("20.00"),
            total_amount=Decimal("20.00"),
        )
        OrderItem.objects.create(
            order=order, product=product, quantity=2,
            unit_price=Decimal("20.00"), total_price=Decimal("40.00"),
        )
        self.assertEqual(self.customer.total_orders, 1)

    def test_total_spent_zero(self):
        self.assertEqual(self.customer.total_spent, Decimal("0"))

    def test_total_spent_with_orders(self):
        Order.objects.create(
            customer=self.customer,
            total_amount=Decimal("150.00"),
        )
        Order.objects.create(
            customer=self.customer,
            total_amount=Decimal("250.00"),
        )
        self.assertEqual(self.customer.total_spent, Decimal("400.00"))

    def test_ordering(self):
        c2 = Customer.objects.create(first_name="Zara", last_name="Ahmed")
        customers = list(Customer.objects.all())
        self.assertEqual(customers[0].first_name, "Zara")
        self.assertEqual(customers[1].first_name, "Ali")


# =============================================================================
# Model Tests - Order
# =============================================================================

class OrderModelTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Test", last_name="Customer",
        )

    def test_str(self):
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        self.assertIn("ORD-", str(order))
        self.assertIn("Test Customer", str(order))

    def test_auto_order_number(self):
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        self.assertTrue(order.order_number.startswith("ORD-"))
        self.assertEqual(len(order.order_number), 10)  # ORD-000001

    def test_order_number_sequential(self):
        o1 = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        o2 = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("50.00"),
            total_amount=Decimal("50.00"),
        )
        self.assertNotEqual(o1.order_number, o2.order_number)
        self.assertEqual(int(o1.order_number.split("-")[1]) + 1,
                         int(o2.order_number.split("-")[1]))

    def test_unique_order_number(self):
        o1 = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        o2 = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("50.00"),
            total_amount=Decimal("50.00"),
        )
        self.assertNotEqual(o1.order_number, o2.order_number)

    def test_order_defaults(self):
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        self.assertEqual(order.payment_method, Order.PaymentMethod.CASH)
        self.assertEqual(order.status, Order.OrderStatus.COMPLETED)
        self.assertEqual(order.tax_amount, Decimal("0"))
        self.assertEqual(order.discount_amount, Decimal("0"))

    def test_order_choices(self):
        for choice in Order.PaymentMethod:
            order = Order.objects.create(
                customer=self.customer,
                payment_method=choice,
                subtotal=Decimal("10.00"),
                total_amount=Decimal("10.00"),
            )
            self.assertEqual(order.payment_method, choice)

        for choice in Order.OrderStatus:
            order = Order.objects.create(
                customer=self.customer,
                status=choice,
                subtotal=Decimal("10.00"),
                total_amount=Decimal("10.00"),
            )
            self.assertEqual(order.status, choice)


# =============================================================================
# Model Tests - OrderItem
# =============================================================================

class OrderItemModelTest(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(first_name="Test")
        self.product = make_product()
        self.order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("40.00"),
            total_amount=Decimal("40.00"),
        )

    def test_str(self):
        item = OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=3, unit_price=Decimal("20.00"),
            total_price=Decimal("60.00"),
        )
        self.assertEqual(str(item), "Widget x3")

    def test_save_calculates_total(self):
        item = OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=5, unit_price=Decimal("20.00"),
            total_price=Decimal("0"),  # should be overwritten
        )
        item.refresh_from_db()
        self.assertEqual(item.total_price, Decimal("100.00"))

    def test_order_items_related_name(self):
        OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=2, unit_price=Decimal("20.00"),
            total_price=Decimal("40.00"),
        )
        self.assertEqual(self.order.items.count(), 1)


# =============================================================================
# Form Tests
# =============================================================================

class CustomerFormTest(TestCase):
    def test_valid_data(self):
        form = CustomerForm(data={
            "first_name": "Ali",
            "last_name": "Khan",
            "email": "ali@example.com",
            "phone": "+923011234567",
            "city": "Lahore",
            "address": "123 Main St",
            "notes": "VIP",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_minimal(self):
        form = CustomerForm(data={"first_name": "Ali"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_first_name(self):
        form = CustomerForm(data={"last_name": "Khan"})
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)

    def test_email_optional(self):
        form = CustomerForm(data={"first_name": "Ali"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_phone_optional(self):
        form = CustomerForm(data={"first_name": "Ali"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_unique_email_constraint(self):
        Customer.objects.create(first_name="A", email="dup@example.com")
        form = CustomerForm(data={
            "first_name": "B",
            "email": "dup@example.com",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_unique_phone_constraint(self):
        Customer.objects.create(first_name="A", phone="+923001234567")
        form = CustomerForm(data={
            "first_name": "B",
            "phone": "+923001234567",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)


# =============================================================================
# View Tests - All require login
# =============================================================================

class CustomerViewAuthTest(TestCase):
    """All customer views require login."""

    def setUp(self):
        self.client = Client()
        self.customer = Customer.objects.create(
            first_name="Test", last_name="User",
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("customers:customer_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_create_requires_login(self):
        response = self.client.get(reverse("customers:customer_create"))
        self.assertEqual(response.status_code, 302)

    def test_detail_requires_login(self):
        response = self.client.get(
            reverse("customers:customer_detail", args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_update_requires_login(self):
        response = self.client.get(
            reverse("customers:customer_update", args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_delete_requires_login(self):
        response = self.client.post(
            reverse("customers:customer_delete", args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_order_detail_requires_login(self):
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        response = self.client.get(
            reverse("customers:order_detail", args=[order.pk])
        )
        self.assertEqual(response.status_code, 302)


# =============================================================================
# View Tests - Customer List
# =============================================================================

class CustomerListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.force_login(self.user)
        self.url = reverse("customers:customer_list")

    def test_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_shows_customers(self):
        Customer.objects.create(first_name="Ali", last_name="Khan")
        Customer.objects.create(first_name="Sara", last_name="Ahmed")
        response = self.client.get(self.url)
        self.assertContains(response, "Ali")
        self.assertContains(response, "Sara")

    def test_hides_deleted(self):
        c = Customer.objects.create(first_name="Deleted")
        c.delete()
        response = self.client.get(self.url)
        self.assertNotContains(response, "Deleted")

    def test_search_by_name(self):
        Customer.objects.create(first_name="Ali", last_name="Khan")
        Customer.objects.create(first_name="Sara", last_name="Ahmed")
        response = self.client.get(f"{self.url}?search=Ali")
        self.assertContains(response, "Ali")
        self.assertNotContains(response, "Sara")

    def test_search_by_email(self):
        Customer.objects.create(first_name="Ali", email="ali@test.com")
        Customer.objects.create(first_name="Sara", email="sara@test.com")
        response = self.client.get(f"{self.url}?search=ali@test.com")
        self.assertContains(response, "Ali")
        self.assertNotContains(response, "Sara")

    def test_search_by_phone(self):
        Customer.objects.create(first_name="Ali", phone="+923001111111")
        Customer.objects.create(first_name="Sara", phone="+923002222222")
        response = self.client.get(f"{self.url}?search=+923001111111")
        self.assertContains(response, "Ali")
        self.assertNotContains(response, "Sara")

    def test_sort_by_name_asc(self):
        Customer.objects.create(first_name="Zara")
        Customer.objects.create(first_name="Ali")
        response = self.client.get(f"{self.url}?sort=first_name")
        content = response.content.decode()
        ali_pos = content.find("Ali")
        zara_pos = content.find("Zara")
        self.assertLess(ali_pos, zara_pos)

    def test_sort_by_name_desc(self):
        Customer.objects.create(first_name="Zara")
        Customer.objects.create(first_name="Ali")
        response = self.client.get(f"{self.url}?sort=-first_name")
        content = response.content.decode()
        zara_pos = content.find("Zara")
        ali_pos = content.find("Ali")
        self.assertLess(zara_pos, ali_pos)

    def test_invalid_sort_ignored(self):
        response = self.client.get(f"{self.url}?sort=invalid_field")
        self.assertEqual(response.status_code, 200)

    def test_pagination(self):
        for i in range(25):
            Customer.objects.create(first_name=f"Customer{i}")
        response = self.client.get(self.url)
        self.assertContains(response, "Next")
        response = self.client.get(f"{self.url}?page=2")
        self.assertEqual(response.status_code, 200)


# =============================================================================
# View Tests - Customer Create
# =============================================================================

class CustomerCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.force_login(self.user)
        self.url = reverse("customers:customer_create")

    def test_get_returns_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Customer")

    def test_post_creates_customer(self):
        response = self.client.post(self.url, {
            "first_name": "Ali",
            "last_name": "Khan",
            "email": "ali@example.com",
            "phone": "+923011234567",
            "city": "Lahore",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(first_name="Ali").exists())

    def test_post_redirects_to_list(self):
        response = self.client.post(self.url, {
            "first_name": "Ali",
        })
        self.assertRedirects(response, reverse("customers:customer_list"))

    def test_post_invalid_returns_form(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.exists())

    def test_post_rejects_get(self):
        """Only GET and POST allowed via require_http_methods."""
        response = self.client.put(self.url)
        self.assertEqual(response.status_code, 405)


# =============================================================================
# View Tests - Customer Detail
# =============================================================================

class CustomerDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(
            first_name="Ali", last_name="Khan",
            email="ali@example.com", city="Lahore",
        )

    def test_detail_page(self):
        url = reverse("customers:customer_detail", args=[self.customer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ali Khan")
        self.assertContains(response, "ali@example.com")

    def test_detail_404_for_deleted(self):
        self.customer.delete()
        url = reverse("customers:customer_detail", args=[self.customer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_404_for_invalid_pk(self):
        url = reverse("customers:customer_detail", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_shows_orders(self):
        order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
        )
        url = reverse("customers:customer_detail", args=[self.customer.pk])
        response = self.client.get(url)
        self.assertContains(response, order.order_number)

    def test_detail_shows_no_orders_message(self):
        url = reverse("customers:customer_detail", args=[self.customer.pk])
        response = self.client.get(url)
        self.assertContains(response, "No orders yet")


# =============================================================================
# View Tests - Customer Update
# =============================================================================

class CustomerUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(
            first_name="Ali", last_name="Khan",
        )

    def test_get_returns_form(self):
        url = reverse("customers:customer_update", args=[self.customer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit")

    def test_post_updates_customer(self):
        url = reverse("customers:customer_update", args=[self.customer.pk])
        response = self.client.post(url, {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@example.com",
        })
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, "Updated")

    def test_post_redirects_to_detail(self):
        url = reverse("customers:customer_update", args=[self.customer.pk])
        response = self.client.post(url, {
            "first_name": "Updated",
        })
        self.assertRedirects(
            response,
            reverse("customers:customer_detail", args=[self.customer.pk]),
        )

    def test_update_deleted_customer_404(self):
        self.customer.delete()
        url = reverse("customers:customer_update", args=[self.customer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post_invalid_returns_form(self):
        url = reverse("customers:customer_update", args=[self.customer.pk])
        response = self.client.post(url, {})  # missing required first_name
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, "Ali")


# =============================================================================
# View Tests - Customer Delete
# =============================================================================

class CustomerDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(first_name="ToDelete")

    def test_post_soft_deletes(self):
        url = reverse("customers:customer_delete", args=[self.customer.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_deleted)
        # Gone from default queryset
        self.assertEqual(Customer.objects.count(), 0)
        # Still in DB
        self.assertEqual(Customer.all_objects.count(), 1)

    def test_get_not_allowed(self):
        url = reverse("customers:customer_delete", args=[self.customer.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_delete_redirects_to_list(self):
        url = reverse("customers:customer_delete", args=[self.customer.pk])
        response = self.client.post(url)
        self.assertRedirects(response, reverse("customers:customer_list"))

    def test_delete_404_for_already_deleted(self):
        self.customer.delete()
        url = reverse("customers:customer_delete", args=[self.customer.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


# =============================================================================
# View Tests - Order Detail
# =============================================================================

class OrderDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123",
        )
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(first_name="Ali")
        self.product = make_product()
        self.order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal("40.00"),
            total_amount=Decimal("40.00"),
            notes="Test note",
        )
        self.order_item = OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=2, unit_price=Decimal("20.00"),
            total_price=Decimal("40.00"),
        )

    def test_order_detail_page(self):
        url = reverse("customers:order_detail", args=[self.order.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_order_detail_shows_items(self):
        url = reverse("customers:order_detail", args=[self.order.pk])
        response = self.client.get(url)
        self.assertContains(response, "Widget")
        self.assertContains(response, "2")

    def test_order_detail_shows_summary(self):
        url = reverse("customers:order_detail", args=[self.order.pk])
        response = self.client.get(url)
        self.assertContains(response, "40.00")

    def test_order_detail_shows_notes(self):
        url = reverse("customers:order_detail", args=[self.order.pk])
        response = self.client.get(url)
        self.assertContains(response, "Test note")

    def test_order_detail_404(self):
        url = reverse("customers:order_detail", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# =============================================================================
# URL Resolution Tests
# =============================================================================

class URLResolutionTest(TestCase):
    def test_customer_list(self):
        self.assertEqual(reverse("customers:customer_list"), "/customers/")

    def test_customer_create(self):
        self.assertEqual(reverse("customers:customer_create"), "/customers/add/")

    def test_customer_detail(self):
        self.assertEqual(
            reverse("customers:customer_detail", args=[1]),
            "/customers/1/",
        )

    def test_customer_update(self):
        self.assertEqual(
            reverse("customers:customer_update", args=[1]),
            "/customers/1/edit/",
        )

    def test_customer_delete(self):
        self.assertEqual(
            reverse("customers:customer_delete", args=[1]),
            "/customers/1/delete/",
        )

    def test_order_detail(self):
        self.assertEqual(
            reverse("customers:order_detail", args=[1]),
            "/customers/orders/1/",
        )
