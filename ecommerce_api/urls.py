from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/catalog/', include('catalog.urls')),
    path('api/v1/orders/', include('orders.urls')),

    path('api/v1/accounts/', include('allauth.urls')),
    path('admin/', admin.site.urls),
]
