from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import Order
from .serializers import OrderCreateSerializer, OrderListSerializer
from .permissions import IsCustomerOrAdminReadOnly
from .tasks import send_order_notifications

User = get_user_model()

class OrderListCreateAPIView(generics.ListCreateAPIView):
    """
    List customer's orders or create a new order
    """
    permission_classes = [IsCustomerOrAdminReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return Order.objects.all()
        return Order.objects.filter(customer=self.request.user)
    
    def perform_create(self, serializer):
        # Set customer and details from authenticated user
        user = self.request.user

        # Ensure only customers can place orders
        if not user.is_customer:
            return Response(
                data='Only customers can place orders',
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = serializer.save(
            customer=user,
            customer_email=serializer.validated_data.get('customer_email') or user.email,
            customer_phone=serializer.validated_data.get('customer_phone') or user.phone_number,
            delivery_address=serializer.validated_data.get('delivery_address') or user.address,
        )

        # Send notifications
        send_order_notifications.delay(order.id)      

class OrderDetailAPIView(generics.RetrieveAPIView):
    """
    Retrieve a specific order
    Customers can only see their orders
    """
    # TODO: Add permissions to limit to only authenticated users
    serializer_class = OrderListSerializer
    
    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user)