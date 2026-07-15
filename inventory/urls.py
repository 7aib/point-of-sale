from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.inventory_dashboard, name="dashboard"),
    path("movements/", views.movement_list, name="movement_list"),
    path("adjust/", views.stock_adjust, name="stock_adjust"),
    path("alerts/", views.alert_list, name="alert_list"),
    path("alerts/<int:pk>/acknowledge/", views.alert_acknowledge, name="alert_acknowledge"),
    path("alerts/<int:pk>/resolve/", views.alert_resolve, name="alert_resolve"),
]
