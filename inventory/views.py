from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, F

from config import ORDERS_PER_PAGE
from products.models import Product
from .models import StockMovement, LowStockAlert
from .forms import StockAdjustmentForm


# =============================================================================
# Inventory Dashboard
# =============================================================================

@login_required
def inventory_dashboard(request):
    total_products = Product.objects.filter(is_active=True, is_deleted=False).count()
    low_stock_products = Product.objects.filter(
        is_active=True, is_deleted=False,
        stock_quantity__lte=F("low_stock_threshold"),
        stock_quantity__gt=0,
    )
    out_of_stock = Product.objects.filter(
        is_active=True, is_deleted=False, stock_quantity=0,
    )
    pending_alerts = LowStockAlert.objects.filter(status="pending")

    return render(request, "inventory/dashboard.html", {
        "total_products": total_products,
        "low_stock_products": low_stock_products,
        "low_stock_count": low_stock_products.count(),
        "out_of_stock_products": out_of_stock,
        "out_of_stock_count": out_of_stock.count(),
        "pending_alerts": pending_alerts,
        "pending_alerts_count": pending_alerts.count(),
    })


# =============================================================================
# Stock Movements
# =============================================================================

@login_required
def movement_list(request):
    queryset = StockMovement.objects.select_related("product", "performed_by")

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(product__name__icontains=search)
            | Q(product__sku__icontains=search)
            | Q(reference__icontains=search)
        )

    # Filter by movement type
    movement_type = request.GET.get("type", "")
    if movement_type:
        queryset = queryset.filter(movement_type=movement_type)

    # Sorting
    sort = request.GET.get("sort", "-created_at")
    allowed_sorts = [
        "created_at", "-created_at",
        "product__name", "-product__name",
        "quantity", "-quantity",
        "movement_type", "-movement_type",
    ]
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)

    paginator = Paginator(queryset, ORDERS_PER_PAGE)
    page = request.GET.get("page")
    movements = paginator.get_page(page)

    return render(request, "inventory/movement_list.html", {
        "movements": movements,
        "search": search,
        "movement_type": movement_type,
        "sort": sort,
    })


@login_required
@require_http_methods(["GET", "POST"])
def stock_adjust(request):
    if request.method == "POST":
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.performed_by = request.user

            # Update product stock
            product = movement.product
            product.stock_quantity += movement.quantity
            product.save(update_fields=["stock_quantity"])

            # Set running stock
            movement.running_stock = product.stock_quantity
            movement.save()

            # Check for low stock alert
            if product.is_low_stock:
                LowStockAlert.objects.get_or_create(
                    product=product,
                    current_stock=product.stock_quantity,
                    threshold=product.low_stock_threshold,
                    status="pending",
                )

            messages.success(request, f"Stock adjusted: {product.name} ({movement.quantity:+d})")
            return redirect("inventory:movement_list")
    else:
        form = StockAdjustmentForm()
    return render(request, "inventory/stock_adjust.html", {"form": form})


# =============================================================================
# Low Stock Alerts
# =============================================================================

@login_required
def alert_list(request):
    queryset = LowStockAlert.objects.select_related("product")

    # Filter by status
    status = request.GET.get("status", "")
    if status:
        queryset = queryset.filter(status=status)
    else:
        # Default: show pending and acknowledged
        queryset = queryset.exclude(status="resolved")

    paginator = Paginator(queryset, ORDERS_PER_PAGE)
    page = request.GET.get("page")
    alerts = paginator.get_page(page)

    return render(request, "inventory/alert_list.html", {
        "alerts": alerts,
        "status": status,
    })


@login_required
@require_http_methods(["POST"])
def alert_acknowledge(request, pk):
    alert = LowStockAlert.objects.get(pk=pk)
    alert.status = "acknowledged"
    alert.save(update_fields=["status"])
    messages.success(request, f"Alert acknowledged for {alert.product.name}")
    return redirect("inventory:alert_list")


@login_required
@require_http_methods(["POST"])
def alert_resolve(request, pk):
    alert = LowStockAlert.objects.get(pk=pk)
    alert.status = "resolved"
    alert.save(update_fields=["status"])
    messages.success(request, f"Alert resolved for {alert.product.name}")
    return redirect("inventory:alert_list")
