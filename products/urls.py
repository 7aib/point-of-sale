from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    # Categories (must come before <slug:slug>/ to avoid conflict)
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_create"),
    path("categories/<slug:slug>/edit/", views.category_update, name="category_update"),
    path("categories/<slug:slug>/delete/", views.category_delete, name="category_delete"),
    # Products
    path("", views.product_list, name="product_list"),
    path("add/", views.product_create, name="product_create"),
    path("<slug:slug>/", views.product_detail, name="product_detail"),
    path("<slug:slug>/edit/", views.product_update, name="product_update"),
    path("<slug:slug>/delete/", views.product_delete, name="product_delete"),
]
