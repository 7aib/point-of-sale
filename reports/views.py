from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from django.db.models.functions import TruncDate, TruncMonth, TruncHour
from django.utils.dateparse import parse_date

from datetime import timedelta
from decimal import Decimal

from customers.models import Order, OrderItem, Customer
from products.models import Product, Category
from sales.models import Payment


@login_required
def dashboard(request):
    today = timezone.now().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    last_30 = today - timedelta(days=30)

    # KPIs
    total_revenue = Order.objects.filter(status="completed").aggregate(t=Sum("total_amount"))["t"] or 0
    total_orders = Order.objects.filter(status="completed").count()
    avg_order = Order.objects.filter(status="completed").aggregate(a=Avg("total_amount"))["a"] or 0
    total_customers = Customer.objects.filter(is_deleted=False).count()
    total_products = Product.objects.filter(is_deleted=False).count()
    low_stock = Product.objects.filter(is_deleted=False, is_active=True, stock_quantity__lte=F("low_stock_threshold")).count()

    # Period revenue
    today_revenue = Order.objects.filter(status="completed", created_at__date=today).aggregate(t=Sum("total_amount"))["t"] or 0
    month_revenue = Order.objects.filter(status="completed", created_at__date__gte=month_start).aggregate(t=Sum("total_amount"))["t"] or 0

    # Revenue last 30 days
    revenue_30d = Order.objects.filter(
        status="completed", created_at__date__gte=last_30
    ).aggregate(t=Sum("total_amount"))["t"] or 0

    return render(request, "reports/dashboard.html", {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order": avg_order,
        "total_customers": total_customers,
        "total_products": total_products,
        "low_stock": low_stock,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "revenue_30d": revenue_30d,
    })


@login_required
def sales_report(request):
    # Date range
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    today = timezone.now().date()
    if not date_from:
        date_from = (today - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = today.isoformat()

    try:
        d_from = timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
        d_to = timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError:
        d_from = today - timedelta(days=30)
        d_to = today

    orders = Order.objects.filter(
        created_at__date__gte=d_from,
        created_at__date__lte=d_to,
    )

    # Summary stats
    total_revenue = orders.filter(status="completed").aggregate(t=Sum("total_amount"))["t"] or 0
    total_orders = orders.count()
    completed_orders = orders.filter(status="completed").count()
    cancelled_orders = orders.filter(status="cancelled").count()
    refunded_orders = orders.filter(status="refunded").count()
    avg_order_val = orders.filter(status="completed").aggregate(a=Avg("total_amount"))["a"] or 0
    total_tax = orders.filter(status="completed").aggregate(t=Sum("tax_amount"))["t"] or 0
    total_discount = orders.filter(status="completed").aggregate(t=Sum("discount_amount"))["t"] or 0

    # Top products
    top_products = OrderItem.objects.filter(
        order__created_at__date__gte=d_from,
        order__created_at__date__lte=d_to,
        order__status="completed",
    ).values("product__name").annotate(
        qty=Sum("quantity"),
        revenue=Sum("total_price"),
    ).order_by("-revenue")[:10]

    # Top categories
    top_categories = OrderItem.objects.filter(
        order__created_at__date__gte=d_from,
        order__created_at__date__lte=d_to,
        order__status="completed",
    ).values("product__category__name").annotate(
        qty=Sum("quantity"),
        revenue=Sum("total_price"),
    ).order_by("-revenue")[:10]

    # Payment method breakdown
    payment_methods = orders.filter(status="completed").values("payment_method").annotate(
        count=Count("id"),
        total=Sum("total_amount"),
    ).order_by("-total")

    # Daily revenue for chart
    daily_revenue = orders.filter(status="completed").annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        revenue=Sum("total_amount"),
        count=Count("id"),
    ).order_by("date")

    # Hourly orders for chart
    hourly_orders = orders.filter(status="completed").annotate(
        hour=TruncHour("created_at")
    ).values("hour").annotate(
        count=Count("id"),
        revenue=Sum("total_amount"),
    ).order_by("hour")

    return render(request, "reports/sales_report.html", {
        "date_from": date_from,
        "date_to": date_to,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "refunded_orders": refunded_orders,
        "avg_order_val": avg_order_val,
        "total_tax": total_tax,
        "total_discount": total_discount,
        "top_products": top_products,
        "top_categories": top_categories,
        "payment_methods": payment_methods,
        "daily_revenue": list(daily_revenue),
        "hourly_orders": list(hourly_orders),
    })


@login_required
def product_report(request):
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    d_from = parse_date(date_from) if date_from else None
    d_to = parse_date(date_to) if date_to else None

    products = Product.objects.filter(is_deleted=False).annotate(
        total_sold=Count("order_items"),
        total_revenue=Sum("order_items__total_price"),
    ).order_by("-total_revenue")

    if d_from:
        products = products.filter(order_items__order__created_at__date__gte=d_from).distinct()
    if d_to:
        products = products.filter(order_items__order__created_at__date__lte=d_to).distinct()

    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count("products"),
        total_sold=Count("products__order_items"),
        total_revenue=Sum("products__order_items__total_price"),
    ).order_by("-total_revenue")

    if d_from:
        categories = categories.filter(products__order_items__order__created_at__date__gte=d_from).distinct()
    if d_to:
        categories = categories.filter(products__order_items__order__created_at__date__lte=d_to).distinct()

    low_stock_products = Product.objects.filter(
        is_deleted=False, is_active=True,
        stock_quantity__lte=F("low_stock_threshold"),
    ).order_by("stock_quantity")

    return render(request, "reports/product_report.html", {
        "products": products,
        "categories": categories,
        "low_stock_products": low_stock_products,
        "date_from": date_from,
        "date_to": date_to,
    })


@login_required
def customer_report(request):
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    d_from = parse_date(date_from) if date_from else None
    d_to = parse_date(date_to) if date_to else None

    # Top customers by revenue
    top_customers = Customer.objects.filter(is_deleted=False).annotate(
        order_count=Count("orders"),
        revenue=Sum("orders__total_amount"),
    ).filter(order_count__gt=0)

    if d_from:
        top_customers = top_customers.filter(orders__created_at__date__gte=d_from)
    if d_to:
        top_customers = top_customers.filter(orders__created_at__date__lte=d_to)

    top_customers = top_customers.distinct().order_by("-revenue")[:20]

    # Customer acquisition (new customers per month, last 12 months)
    twelve_months_ago = timezone.now() - timedelta(days=365)
    customer_acquisition = Customer.objects.filter(
        is_deleted=False,
        created_at__gte=twelve_months_ago,
    ).annotate(
        month=TruncMonth("created_at")
    ).values("month").annotate(
        count=Count("id"),
    ).order_by("month")

    # Total customers
    total_customers = Customer.objects.filter(is_deleted=False).count()
    customers_with_orders = Customer.objects.filter(is_deleted=False, orders__isnull=False).distinct().count()

    return render(request, "reports/customer_report.html", {
        "top_customers": top_customers,
        "customer_acquisition": list(customer_acquisition),
        "total_customers": total_customers,
        "customers_with_orders": customers_with_orders,
        "date_from": date_from,
        "date_to": date_to,
    })


# =============================================================================
# API Endpoints for Charts
# =============================================================================

@login_required
def chart_daily_revenue(request):
    days = int(request.GET.get("days", 30))
    d_from = timezone.now().date() - timedelta(days=days)

    data = Order.objects.filter(
        status="completed",
        created_at__date__gte=d_from,
    ).annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        revenue=Sum("total_amount"),
        count=Count("id"),
    ).order_by("date")

    return JsonResponse({
        "labels": [d["date"].strftime("%b %d") for d in data],
        "revenue": [float(d["revenue"] or 0) for d in data],
        "orders": [d["count"] for d in data],
    })


@login_required
def chart_payment_methods(request):
    days = int(request.GET.get("days", 30))
    d_from = timezone.now().date() - timedelta(days=days)

    data = Order.objects.filter(
        status="completed",
        created_at__date__gte=d_from,
    ).values("payment_method").annotate(
        count=Count("id"),
        total=Sum("total_amount"),
    ).order_by("-total")

    labels_map = {"cash": "Cash", "card": "Card", "bank_transfer": "Bank Transfer", "credit": "Credit", "other": "Other"}

    return JsonResponse({
        "labels": [labels_map.get(d["payment_method"], d["payment_method"]) for d in data],
        "values": [float(d["total"] or 0) for d in data],
        "counts": [d["count"] for d in data],
    })


@login_required
def chart_top_products(request):
    days = int(request.GET.get("days", 30))
    d_from = timezone.now().date() - timedelta(days=days)

    data = OrderItem.objects.filter(
        order__status="completed",
        order__created_at__date__gte=d_from,
    ).values("product__name").annotate(
        qty=Sum("quantity"),
        revenue=Sum("total_price"),
    ).order_by("-revenue")[:10]

    return JsonResponse({
        "labels": [d["product__name"] for d in data],
        "quantity": [d["qty"] for d in data],
        "revenue": [float(d["revenue"] or 0) for d in data],
    })


@login_required
def chart_category_revenue(request):
    days = int(request.GET.get("days", 30))
    d_from = timezone.now().date() - timedelta(days=days)

    data = OrderItem.objects.filter(
        order__status="completed",
        order__created_at__date__gte=d_from,
    ).values("product__category__name").annotate(
        revenue=Sum("total_price"),
    ).order_by("-revenue")[:8]

    return JsonResponse({
        "labels": [d["product__category__name"] or "Uncategorized" for d in data],
        "values": [float(d["revenue"] or 0) for d in data],
    })


@login_required
def chart_order_status(request):
    days = int(request.GET.get("days", 30))
    d_from = timezone.now().date() - timedelta(days=days)

    data = Order.objects.filter(
        created_at__date__gte=d_from,
    ).values("status").annotate(
        count=Count("id"),
    ).order_by("status")

    labels_map = {"pending": "Pending", "completed": "Completed", "cancelled": "Cancelled", "refunded": "Refunded"}
    colors = {"pending": "#f59e0b", "completed": "#16a34a", "cancelled": "#dc2626", "refunded": "#6b7280"}

    return JsonResponse({
        "labels": [labels_map.get(d["status"], d["status"]) for d in data],
        "values": [d["count"] for d in data],
        "colors": [colors.get(d["status"], "#6b7280") for d in data],
    })


@login_required
def chart_hourly_orders(request):
    days = int(request.GET.get("days", 7))
    d_from = timezone.now().date() - timedelta(days=days)

    data = Order.objects.filter(
        status="completed",
        created_at__date__gte=d_from,
    ).annotate(
        hour=TruncHour("created_at")
    ).values("hour").annotate(
        count=Count("id"),
        revenue=Sum("total_amount"),
    ).order_by("hour")

    return JsonResponse({
        "labels": [d["hour"].strftime("%b %d %H:00") for d in data],
        "counts": [d["count"] for d in data],
        "revenue": [float(d["revenue"] or 0) for d in data],
    })
