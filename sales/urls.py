from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # POS Terminal
    path("terminal/", views.pos_terminal, name="pos_terminal"),
    path("api/barcode/", views.barcode_lookup, name="barcode_lookup"),
    path("api/create-order/", views.pos_create_order, name="pos_create_order"),
    # Orders
    path("orders/", views.order_list, name="order_list"),
    path("orders/create/", views.order_create, name="order_create"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/edit/", views.order_update, name="order_update"),
    path("orders/<int:pk>/delete/", views.order_delete, name="order_delete"),
    path("orders/<int:pk>/status/", views.order_status_update, name="order_status_update"),
    # Payments
    path("orders/<int:order_pk>/pay/", views.payment_create, name="payment_create"),
    path("payments/<int:pk>/refund/", views.payment_refund, name="payment_refund"),
    # Quick Sale
    path("quick-sale/", views.quick_sale, name="quick_sale"),
]
