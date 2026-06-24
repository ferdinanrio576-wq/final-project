from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin-django/', admin.site.urls), # Django built-in admin site
    path('admin/', include('dashboard.urls')), # Custom responsive Admin Dashboard
    path('', include('products.urls')), # Catalog, reviews
    path('', include('users.urls')), # Profile, addresses, auth
    path('cart/', include('orders.urls')), # Cart, orders, checkout
    path('payments/', include('payments.urls')), # Payment simulation
    path('api/', include('api.urls')), # REST API for AJAX and dynamic calls
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
