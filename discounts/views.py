from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q

from config import PRODUCTS_PER_PAGE
from .models import Discount, Coupon
from .forms import DiscountForm, CouponForm


# =============================================================================
# Discount Views
# =============================================================================

@login_required
def discount_list(request):
    queryset = Discount.objects.all()

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))

    # Filter by type
    discount_type = request.GET.get("type", "")
    if discount_type in ("percentage", "fixed"):
        queryset = queryset.filter(discount_type=discount_type)

    # Filter by status
    status = request.GET.get("status", "")
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    elif status == "expired":
        from django.utils import timezone
        queryset = queryset.filter(valid_to__lt=timezone.now())

    # Sorting
    sort = request.GET.get("sort", "-created_at")
    allowed_sorts = [
        "name", "-name", "code", "-code",
        "discount_type", "value", "-value",
        "created_at", "-created_at", "valid_to", "-valid_to",
    ]
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)

    paginator = Paginator(queryset, PRODUCTS_PER_PAGE)
    page = request.GET.get("page")
    discounts = paginator.get_page(page)

    return render(request, "discounts/discount_list.html", {
        "discounts": discounts,
        "search": search,
        "discount_type": discount_type,
        "status": status,
        "sort": sort,
    })


@login_required
@require_http_methods(["GET", "POST"])
def discount_create(request):
    if request.method == "POST":
        form = DiscountForm(request.POST)
        if form.is_valid():
            discount = form.save()
            messages.success(request, f"Discount '{discount.name}' created successfully!")
            return redirect("discounts:discount_list")
    else:
        form = DiscountForm()
    return render(request, "discounts/discount_form.html", {"form": form, "title": "Add Discount"})


@login_required
def discount_detail(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    return render(request, "discounts/discount_detail.html", {"discount": discount})


@login_required
@require_http_methods(["GET", "POST"])
def discount_update(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    if request.method == "POST":
        form = DiscountForm(request.POST, instance=discount)
        if form.is_valid():
            form.save()
            messages.success(request, f"Discount '{discount.name}' updated successfully!")
            return redirect("discounts:discount_detail", pk=discount.pk)
    else:
        form = DiscountForm(instance=discount)
    return render(request, "discounts/discount_form.html", {
        "form": form,
        "title": f"Edit {discount.name}",
        "discount": discount,
    })


@login_required
@require_http_methods(["POST"])
def discount_delete(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    discount.delete()
    messages.success(request, f"Discount '{discount.name}' deleted successfully!")
    return redirect("discounts:discount_list")


@login_required
@require_http_methods(["POST"])
def discount_toggle(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    discount.is_active = not discount.is_active
    discount.save(update_fields=["is_active"])
    status = "activated" if discount.is_active else "deactivated"
    messages.success(request, f"Discount '{discount.name}' {status} successfully!")
    return redirect("discounts:discount_list")


# =============================================================================
# Coupon Views
# =============================================================================

@login_required
def coupon_list(request):
    queryset = Coupon.objects.all()

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(code__icontains=search) | Q(description__icontains=search))

    # Filter by type
    discount_type = request.GET.get("type", "")
    if discount_type in ("percentage", "fixed"):
        queryset = queryset.filter(discount_type=discount_type)

    # Filter by status
    status = request.GET.get("status", "")
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    elif status == "expired":
        from django.utils import timezone
        queryset = queryset.filter(valid_to__lt=timezone.now())

    # Sorting
    sort = request.GET.get("sort", "-created_at")
    allowed_sorts = [
        "code", "-code", "discount_type", "discount_value", "-discount_value",
        "used_count", "-used_count", "created_at", "-created_at", "valid_to", "-valid_to",
    ]
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)

    paginator = Paginator(queryset, PRODUCTS_PER_PAGE)
    page = request.GET.get("page")
    coupons = paginator.get_page(page)

    return render(request, "discounts/coupon_list.html", {
        "coupons": coupons,
        "search": search,
        "discount_type": discount_type,
        "status": status,
        "sort": sort,
    })


@login_required
@require_http_methods(["GET", "POST"])
def coupon_create(request):
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save()
            messages.success(request, f"Coupon '{coupon.code}' created successfully!")
            return redirect("discounts:coupon_list")
    else:
        form = CouponForm()
    return render(request, "discounts/coupon_form.html", {"form": form, "title": "Add Coupon"})


@login_required
def coupon_detail(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    return render(request, "discounts/coupon_detail.html", {"coupon": coupon})


@login_required
@require_http_methods(["GET", "POST"])
def coupon_update(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, f"Coupon '{coupon.code}' updated successfully!")
            return redirect("discounts:coupon_detail", pk=coupon.pk)
    else:
        form = CouponForm(instance=coupon)
    return render(request, "discounts/coupon_form.html", {
        "form": form,
        "title": f"Edit Coupon {coupon.code}",
        "coupon": coupon,
    })


@login_required
@require_http_methods(["POST"])
def coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    messages.success(request, f"Coupon '{coupon.code}' deleted successfully!")
    return redirect("discounts:coupon_list")


@login_required
@require_http_methods(["POST"])
def coupon_toggle(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=["is_active"])
    status = "activated" if coupon.is_active else "deactivated"
    messages.success(request, f"Coupon '{coupon.code}' {status} successfully!")
    return redirect("discounts:coupon_list")
