from django.urls import path
from catalog import views

app_name = 'catalog'

urlpatterns = [
    path('categories/', view=views.CategoryListCreateAPIView.as_view(), name='category-list'),
    path('categories/<int:pk>/', view=views.CategoryDetailAPIView.as_view(), name='category-detail'),
]