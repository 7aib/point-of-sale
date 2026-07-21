from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.http import JsonResponse
import json

from config import ORDERS_PER_PAGE
from customers.models import Order, OrderItem, Customer
from products.models import Product
from discounts.models import Discount, Coupon
from .models import Payment
from .forms import OrderForm, OrderItemFormSet, PaymentForm, QuickSaleForm


# =============================================================================
# Dashboard
# =============================================================================

@login_required
def dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Today's stats (exclude refunded)
    today_orders = Order.objects.filter(created_at__date=today).exclude(status="refunded")
    today_revenue = today_orders.aggregate(total=Sum("total_amount"))["total"] or 0
    today_count = today_orders.count()

    # This month (exclude refunded)
    month_orders = Order.objects.filter(created_at__date__gte=month_start).exclude(status="refunded")
    month_revenue = month_orders.aggregate(total=Sum("total_amount"))["total"] or 0
    month_count = month_orders.count()

    # All time (exclude refunded)
    total_revenue = Order.objects.exclude(status="refunded").aggregate(total=Sum("total_amount"))["total"] or 0
    total_orders = Order.objects.exclude(status="refunded").count()

    # Pending payments
    pending_orders = Order.objects.filter(
        status="pending"
    ).annotate(
        paid=Sum("payments__amount", filter=Q(payments__status="completed"))
    ).filter(paid__lt=F("total_amount"))[:10]

    # Recent orders
    recent_orders = Order.objects.select_related("customer", "performed_by")[:10]

    # Top products
    top_products = Product.objects.annotate(
        sold=Count("order_items")
    ).order_by("-sold")[:5]

    return render(request, "sales/dashboard.html", {
        "today_revenue": today_revenue,
        "today_count": today_count,
        "month_revenue": month_revenue,
        "month_count": month_count,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "recent_orders": recent_orders,
        "top_products": top_products,
    })


# =============================================================================
# Order Views
# =============================================================================

@login_required
def order_list(request):
    queryset = Order.objects.select_related("customer", "performed_by").exclude(status="refunded")

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(order_number__icontains=search)
            | Q(customer__first_name__icontains=search)
            | Q(customer__last_name__icontains=search)
        )

    # Filter by status
    status = request.GET.get("status", "")
    if status in ("pending", "completed", "cancelled", "refunded"):
        queryset = queryset.filter(status=status)

    # Filter by payment method
    payment_method = request.GET.get("payment_method", "")
    if payment_method in ("cash", "card", "bank_transfer", "credit", "other"):
        queryset = queryset.filter(payment_method=payment_method)

    # Date range
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if date_from:
        try:
            queryset = queryset.filter(created_at__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            queryset = queryset.filter(created_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass

    # Sorting
    sort = request.GET.get("sort", "-created_at")
    allowed_sorts = [
        "order_number", "-order_number",
        "total_amount", "-total_amount",
        "status", "payment_method",
        "created_at", "-created_at",
    ]
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)

    paginator = Paginator(queryset, ORDERS_PER_PAGE)
    page = request.GET.get("page")
    orders = paginator.get_page(page)

    # Summary stats for filters
    total_amount = queryset.aggregate(total=Sum("total_amount"))["total"] or 0

    return render(request, "sales/order_list.html", {
        "orders": orders,
        "search": search,
        "status": status,
        "payment_method": payment_method,
        "date_from": date_from,
        "date_to": date_to,
        "sort": sort,
        "total_amount": total_amount,
    })


@login_required
@require_http_methods(["GET", "POST"])
def order_create(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.performed_by = request.user
            order.save()
            formset.instance = order

            # Set unit prices from products if not provided
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get("unit_price"):
                    product = item_form.cleaned_data.get("product")
                    if product:
                        item_form.instance.unit_price = product.selling_price

            formset.save()
            order.refresh_from_db()
            _recalculate_order_totals(order)
            messages.success(request, f"Order {order.order_number} created successfully!")
            return redirect("sales:order_detail", pk=order.pk)
    else:
        form = OrderForm(initial={"payment_method": Order.PaymentMethod.CASH})
        formset = OrderItemFormSet()

    return render(request, "sales/order_form.html", {
        "form": form,
        "formset": formset,
        "title": "Create New Order",
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer", "performed_by"),
        pk=pk,
    )
    payments = order.payments.all()
    total_paid = payments.filter(status=Payment.PaymentStatus.COMPLETED).aggregate(
        total=Sum("amount")
    )["total"] or 0
    balance = order.total_amount - total_paid

    return render(request, "sales/order_detail.html", {
        "order": order,
        "payments": payments,
        "total_paid": total_paid,
        "balance": balance,
    })


@login_required
@require_http_methods(["GET", "POST"])
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        formset = OrderItemFormSet(request.POST, instance=order)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            _recalculate_order_totals(order)
            messages.success(request, f"Order {order.order_number} updated successfully!")
            return redirect("sales:order_detail", pk=order.pk)
    else:
        form = OrderForm(instance=order)
        formset = OrderItemFormSet(instance=order)

    return render(request, "sales/order_form.html", {
        "form": form,
        "formset": formset,
        "title": f"Edit Order {order.order_number}",
        "order": order,
    })


@login_required
@require_http_methods(["POST"])
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    order_number = order.order_number
    order.delete()
    messages.success(request, f"Order {order_number} deleted successfully!")
    return redirect("sales:order_list")


@login_required
@require_http_methods(["POST"])
def order_status_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get("status", "")
    if new_status in dict(Order.OrderStatus.choices):
        order.status = new_status
        order.save(update_fields=["status"])
        messages.success(request, f"Order {order.order_number} status updated to {order.get_status_display()}.")
    else:
        messages.error(request, "Invalid status.")
    return redirect("sales:order_detail", pk=order.pk)


# =============================================================================
# Payment Views
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def payment_create(request, order_pk):
    order = get_object_or_404(Order, pk=order_pk)
    total_paid = order.payments.filter(
        status=Payment.PaymentStatus.COMPLETED
    ).aggregate(total=Sum("amount"))["total"] or 0
    balance = order.total_amount - total_paid

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.order = order
            payment.received_by = request.user
            payment.save()
            messages.success(request, f"Payment of {payment.amount} recorded successfully!")
            return redirect("sales:order_detail", pk=order.pk)
    else:
        form = PaymentForm(initial={"amount": balance})

    return render(request, "sales/payment_form.html", {
        "form": form,
        "order": order,
        "balance": balance,
        "title": f"Add Payment - {order.order_number}",
    })


@login_required
@require_http_methods(["POST"])
def payment_refund(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if payment.status == Payment.PaymentStatus.COMPLETED:
        payment.status = Payment.PaymentStatus.REFUNDED
        payment.save(update_fields=["status"])

        # Restore stock for all items in the order
        from inventory.models import StockMovement
        for item in payment.order.items.select_related("product").all():
            product = item.product
            product.stock_quantity += item.quantity
            product.save(update_fields=["stock_quantity"])
            StockMovement.objects.create(
                product=product,
                movement_type="in",
                quantity=item.quantity,
                reference=payment.order.order_number,
                notes=f"Refund for {payment.order.order_number}",
                performed_by=request.user,
            )

        # Update order status to refunded
        payment.order.status = "refunded"
        payment.order.save(update_fields=["status"])

        messages.success(request, f"Payment {payment.pk} refunded successfully! Stock restored.")
    else:
        messages.error(request, "Only completed payments can be refunded.")
    return redirect("sales:order_detail", pk=payment.order.pk)


# =============================================================================
# Quick Sale (POS-style)
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def quick_sale(request):
    products = Product.objects.filter(is_active=True, is_deleted=False, stock_quantity__gt=0)

    if request.method == "POST":
        form = QuickSaleForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data.get("customer")
            payment_method = form.cleaned_data["payment_method"]
            notes = form.cleaned_data.get("notes", "")
            discount_code = form.cleaned_data.get("discount_code", "").strip()

            # Create order
            order = Order(
                customer=customer or Customer.objects.filter(is_deleted=False).first(),
                payment_method=payment_method,
                notes=notes,
                performed_by=request.user,
            )
            if not order.customer:
                # Create walk-in customer
                order.customer = Customer.objects.create(
                    first_name="Walk-in",
                    last_name="Customer",
                )
            order.save()

            # Process items from POST data
            product_ids = request.POST.getlist("item_product[]")
            quantities = request.POST.getlist("item_quantity[]")

            for pid, qty in zip(product_ids, quantities):
                try:
                    product = Product.objects.get(pk=pid, is_active=True, is_deleted=False)
                    qty = int(qty)
                    if qty > 0:
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=qty,
                            unit_price=product.selling_price,
                        )
                except (Product.DoesNotExist, ValueError):
                    continue

            if not order.items.exists():
                order.delete()
                messages.error(request, "No items in the order.")
                return redirect("sales:quick_sale")

            # Calculate subtotal from items before discount
            from decimal import Decimal
            current_subtotal = sum(
                item.unit_price * item.quantity for item in order.items.all()
            )

            # Apply discount
            discount_amount = Decimal("0")
            if discount_code:
                # Try Discount first
                try:
                    discount = Discount.objects.get(code__iexact=discount_code, is_active=True)
                    discount_amount = Decimal(str(discount.calculate_discount(current_subtotal)))
                    if discount_amount > 0:
                        discount.used_count += 1
                        discount.save(update_fields=["used_count"])
                except Discount.DoesNotExist:
                    # Try Coupon
                    try:
                        coupon = Coupon.objects.get(code__iexact=discount_code, is_active=True)
                        discount_amount = Decimal(str(coupon.calculate_discount(current_subtotal)))
                        if discount_amount > 0:
                            coupon.redeem()
                    except Coupon.DoesNotExist:
                        messages.warning(request, f"Invalid discount/coupon code: {discount_code}")

            # Recalculate totals
            _recalculate_order_totals(order, discount_amount)

            # Create payment for full amount
            Payment.objects.create(
                order=order,
                amount=order.total_amount,
                payment_method=payment_method,
                status=Payment.PaymentStatus.COMPLETED,
                received_by=request.user,
            )

            messages.success(request, f"Sale completed! Order {order.order_number} - Total: {order.total_amount}")
            return redirect("sales:order_detail", pk=order.pk)

    return render(request, "sales/quick_sale.html", {
        "form": QuickSaleForm(),
        "products": products,
    })


# =============================================================================
# Helpers
# =============================================================================

def _recalculate_order_totals(order, discount_amount=None):
    """Recalculate order subtotal, tax, and total from items."""
    items = order.items.all()
    subtotal = sum(item.total_price for item in items)

    # Calculate tax
    from config import TAX_RATE
    tax_amount = 0
    for item in items:
        if item.product.tax_rate > 0:
            tax_amount += item.total_price * (item.product.tax_rate / 100)
        elif TAX_RATE > 0:
            tax_amount += item.total_price * (TAX_RATE / 100)

    if discount_amount is None:
        discount_amount = order.discount_amount

    order.subtotal = subtotal
    order.tax_amount = round(tax_amount, 2)
    order.discount_amount = discount_amount
    order.total_amount = round(subtotal + tax_amount - discount_amount, 2)
    order.save(update_fields=["subtotal", "tax_amount", "discount_amount", "total_amount"])


# =============================================================================
# POS Terminal
# =============================================================================

@login_required
def pos_terminal(request):
    products = Product.objects.filter(
        is_active=True, is_deleted=False, stock_quantity__gt=0
    ).select_related("category")[:50]

    customers = Customer.objects.filter(is_deleted=False).order_by("first_name")[:100]

    return render(request, "sales/pos_terminal.html", {
        "products": products,
        "customers": customers,
    })


@login_required
@require_http_methods(["GET"])
def barcode_lookup(request):
    """API endpoint: look up a product by barcode or SKU. Returns JSON."""
    code = request.GET.get("code", "").strip()
    if not code:
        return JsonResponse({"error": "No code provided"}, status=400)

    product = Product.objects.filter(
        Q(barcode=code) | Q(sku=code),
        is_active=True, is_deleted=False,
    ).first()

    if not product:
        return JsonResponse({"error": f"No product found for '{code}'"}, status=404)

    return JsonResponse({
        "id": product.pk,
        "name": product.name,
        "sku": product.sku,
        "barcode": product.barcode or "",
        "price": str(product.selling_price),
        "stock": product.stock_quantity,
        "category": product.category.name if product.category else "",
        "tax_rate": str(product.tax_rate),
    })


@login_required
@require_http_methods(["POST"])
def pos_create_order(request):
    """API endpoint: create an order from POS terminal data."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    items = data.get("items", [])
    if not items:
        return JsonResponse({"error": "No items provided"}, status=400)

    customer_id = data.get("customer_id")
    payment_method = data.get("payment_method", "cash")
    discount_code = data.get("discount_code", "").strip()
    notes = data.get("notes", "")

    # Resolve customer
    customer = None
    if customer_id:
        customer = Customer.objects.filter(pk=customer_id, is_deleted=False).first()
    if not customer:
        customer = Customer.objects.filter(is_deleted=False).first()
        if not customer:
            customer = Customer.objects.create(
                first_name="Walk-in", last_name="Customer",
            )

    # Create order
    order = Order(
        customer=customer,
        payment_method=payment_method,
        notes=notes,
        performed_by=request.user,
    )
    order.save()

    # Create items
    for item_data in items:
        try:
            product = Product.objects.get(pk=item_data["id"], is_active=True, is_deleted=False)
            qty = int(item_data.get("quantity", 1))
            if qty > 0 and product.stock_quantity >= qty:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    unit_price=product.selling_price,
                )
                # Deduct stock
                product.stock_quantity -= qty
                product.save(update_fields=["stock_quantity"])
        except (Product.DoesNotExist, KeyError, ValueError):
            continue

    if not order.items.exists():
        order.delete()
        return JsonResponse({"error": "No valid items in order"}, status=400)

    # Calculate subtotal
    from decimal import Decimal
    current_subtotal = sum(
        item.unit_price * item.quantity for item in order.items.all()
    )

    # Apply discount
    discount_amount = Decimal("0")
    if discount_code:
        try:
            discount = Discount.objects.get(code__iexact=discount_code, is_active=True)
            discount_amount = Decimal(str(discount.calculate_discount(current_subtotal)))
            if discount_amount > 0:
                discount.used_count += 1
                discount.save(update_fields=["used_count"])
        except Discount.DoesNotExist:
            try:
                coupon = Coupon.objects.get(code__iexact=discount_code, is_active=True)
                discount_amount = Decimal(str(coupon.calculate_discount(current_subtotal)))
                if discount_amount > 0:
                    coupon.redeem()
            except Coupon.DoesNotExist:
                pass

    _recalculate_order_totals(order, discount_amount)

    # Create payment
    Payment.objects.create(
        order=order,
        amount=order.total_amount,
        payment_method=payment_method,
        status=Payment.PaymentStatus.COMPLETED,
        received_by=request.user,
    )

    return JsonResponse({
        "success": True,
        "order_id": order.pk,
        "order_number": order.order_number,
        "total": str(order.total_amount),
        "subtotal": str(order.subtotal),
        "tax": str(order.tax_amount),
        "discount": str(discount_amount),
        "payment_method": order.get_payment_method_display(),
        "date": order.created_at.strftime("%b %d, %Y %H:%M"),
        "redirect": f"/sales/orders/{order.pk}/",
    })
