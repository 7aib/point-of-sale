from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sales/", views.sales_report, name="sales_report"),
    path("products/", views.product_report, name="product_report"),
    path("customers/", views.customer_report, name="customer_report"),
    # Chart APIs
    path("api/daily-revenue/", views.chart_daily_revenue, name="chart_daily_revenue"),
    path("api/payment-methods/", views.chart_payment_methods, name="chart_payment_methods"),
    path("api/top-products/", views.chart_top_products, name="chart_top_products"),
    path("api/category-revenue/", views.chart_category_revenue, name="chart_category_revenue"),
    path("api/order-status/", views.chart_order_status, name="chart_order_status"),
    path("api/hourly-orders/", views.chart_hourly_orders, name="chart_hourly_orders"),
]
