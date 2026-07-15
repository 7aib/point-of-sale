from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, F

from config import PRODUCTS_PER_PAGE
from .models import Category, Product
from .forms import CategoryForm, ProductForm


# =============================================================================
# Product Views
# =============================================================================

@login_required
def product_list(request):
    queryset = Product.objects.filter(is_deleted=False)

    # Search
    search = request.GET.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(sku__icontains=search)
            | Q(barcode__icontains=search)
        )

    # Filter by category
    category_id = request.GET.get("category", "")
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # Filter by status
    status = request.GET.get("status", "")
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    elif status == "low_stock":
        queryset = queryset.filter(is_active=True, stock_quantity__lte=F("low_stock_threshold"))
    elif status == "out_of_stock":
        queryset = queryset.filter(stock_quantity=0)

    # Sorting
    sort = request.GET.get("sort", "-created_at")
    allowed_sorts = [
        "name", "-name", "sku", "-sku",
        "selling_price", "-selling_price",
        "stock_quantity", "-stock_quantity",
        "created_at", "-created_at",
    ]
    if sort in allowed_sorts:
        queryset = queryset.order_by(sort)

    # Pagination
    paginator = Paginator(queryset, PRODUCTS_PER_PAGE)
    page = request.GET.get("page")
    products = paginator.get_page(page)

    categories = Category.objects.filter(is_active=True)

    return render(request, "products/product_list.html", {
        "products": products,
        "categories": categories,
        "search": search,
        "category_id": category_id,
        "status": status,
        "sort": sort,
    })


@login_required
@require_http_methods(["GET", "POST"])
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' created successfully!")
            return redirect("products:product_list")
    else:
        form = ProductForm()
    return render(request, "products/product_form.html", {"form": form, "title": "Add Product"})


@login_required
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_deleted=False)
    return render(request, "products/product_detail.html", {"product": product})


@login_required
@require_http_methods(["GET", "POST"])
def product_update(request, slug):
    product = get_object_or_404(Product, slug=slug, is_deleted=False)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect("products:product_detail", slug=product.slug)
    else:
        form = ProductForm(instance=product)
    return render(request, "products/product_form.html", {
        "form": form,
        "title": f"Edit {product.name}",
        "product": product,
    })


@login_required
@require_http_methods(["POST"])
def product_delete(request, slug):
    product = get_object_or_404(Product, slug=slug, is_deleted=False)
    product.delete()
    messages.success(request, f"Product '{product.name}' deleted successfully!")
    return redirect("products:product_list")


# =============================================================================
# Category Views
# =============================================================================

@login_required
def category_list(request):
    categories = Category.objects.filter(parent__isnull=True)
    return render(request, "products/category_list.html", {"categories": categories})


@login_required
@require_http_methods(["GET", "POST"])
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully!")
            return redirect("products:category_list")
    else:
        form = CategoryForm()
    return render(request, "products/category_form.html", {"form": form, "title": "Add Category"})


@login_required
@require_http_methods(["GET", "POST"])
def category_update(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully!")
            return redirect("products:category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "products/category_form.html", {
        "form": form,
        "title": f"Edit {category.name}",
        "category": category,
    })


@login_required
@require_http_methods(["POST"])
def category_delete(request, slug):
    category = get_object_or_404(Category, slug=slug)
    category.delete()
    messages.success(request, f"Category '{category.name}' deleted successfully!")
    return redirect("products:category_list")
