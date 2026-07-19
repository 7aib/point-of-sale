from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('inventory/', include('inventory.urls')),
    path('customers/', include('customers.urls')),
    path('discounts/', include('discounts.urls')),
    path('sales/', include('sales.urls')),
    path('reports/', include('reports.urls')),
    path('settings/', views.settings_view, name='settings'),
    path('', RedirectView.as_view(url=reverse_lazy('accounts:login')), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
