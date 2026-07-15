from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count

from config import CUSTOMERS_PER_PAGE
from .models import Customer, Order
from .forms import CustomerForm


@login_required
def customer_list(request):
    queryset = Customer.objects.filter(is_deleted=False)

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )

    # Sorting
    sort = request.GET.get("sort", "-created_at")
    allowed_sorts = [
        "first_name", "-first_name",
        "email", "-email",
        "created_at", "-created_at",
    ]
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)

    paginator = Paginator(queryset, CUSTOMERS_PER_PAGE)
    page = request.GET.get("page")
    customers = paginator.get_page(page)

    return render(request, "customers/customer_list.html", {
        "customers": customers,
        "search": search,
        "sort": sort,
    })


@login_required
@require_http_methods(["GET", "POST"])
def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f"Customer '{customer.full_name}' created successfully!")
            return redirect("customers:customer_list")
    else:
        form = CustomerForm()
    return render(request, "customers/customer_form.html", {"form": form, "title": "Add Customer"})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk, is_deleted=False)
    orders = customer.orders.all()[:10]
    return render(request, "customers/customer_detail.html", {
        "customer": customer,
        "orders": orders,
    })


@login_required
@require_http_methods(["GET", "POST"])
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk, is_deleted=False)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer '{customer.full_name}' updated successfully!")
            return redirect("customers:customer_detail", pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, "customers/customer_form.html", {
        "form": form,
        "title": f"Edit {customer.full_name}",
        "customer": customer,
    })


@login_required
@require_http_methods(["POST"])
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk, is_deleted=False)
    customer.delete()
    messages.success(request, f"Customer '{customer.full_name}' deleted successfully!")
    return redirect("customers:customer_list")


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, "customers/order_detail.html", {"order": order})
