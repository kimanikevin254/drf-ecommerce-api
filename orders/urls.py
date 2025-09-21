from django.urls import path
from orders import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderListCreateAPIView.as_view(), name='order-list'),
    path('<int:pk>/', views.OrderDetailAPIView.as_view(), name='order-detail'),
]