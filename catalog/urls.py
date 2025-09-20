from django.urls import path
from catalog import views

app_name = 'catalog'

urlpatterns = [
    path('categories/', view=views.CategoryListCreateAPIView.as_view(), name='category-list'),
    path('categories/<int:pk>/', view=views.CategoryDetailAPIView.as_view(), name='category-detail'),
    path('categories/<int:pk>/average-price/', view=views.CategoryAveragePriceAPIView.as_view(), name='category-avg-price'),
    path('products/', view=views.ProductListCreateAPIView.as_view(), name='product-list'),
    path('products/<int:pk>/', view=views.ProductDetailAPIView.as_view(), name='product-detail')
]