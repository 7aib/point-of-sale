from django.urls import path

from . import views

app_name = "discounts"

urlpatterns = [
    # Discounts
    path("", views.discount_list, name="discount_list"),
    path("add/", views.discount_create, name="discount_create"),
    path("<int:pk>/", views.discount_detail, name="discount_detail"),
    path("<int:pk>/edit/", views.discount_update, name="discount_update"),
    path("<int:pk>/delete/", views.discount_delete, name="discount_delete"),
    path("<int:pk>/toggle/", views.discount_toggle, name="discount_toggle"),
    # Coupons
    path("coupons/", views.coupon_list, name="coupon_list"),
    path("coupons/add/", views.coupon_create, name="coupon_create"),
    path("coupons/<int:pk>/", views.coupon_detail, name="coupon_detail"),
    path("coupons/<int:pk>/edit/", views.coupon_update, name="coupon_update"),
    path("coupons/<int:pk>/delete/", views.coupon_delete, name="coupon_delete"),
    path("coupons/<int:pk>/toggle/", views.coupon_toggle, name="coupon_toggle"),
]
