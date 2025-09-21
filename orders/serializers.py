from rest_framework import serializers
from django.db import transaction

from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'subtotal']
        read_only_fields = ['price']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Quantity must be greater than 0'
            )
        return value

class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_amount = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'customer_email', 'customer_phone', 'delivery_address',
            'items', 'total_amount'
        ]

    def validate(self, data):
        # Extract items from the data
        items_data = data.get('items', [])

        # Check stock for all items
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']

            if product.stock_quantity < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {quantity}"
                )
            
        return data

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                'Order must have at least one item'
            )
        return value
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')

        
        with transaction.atomic(): # Ensure all-or-nothing
            # Create order
            order = Order.objects.create(total_amount=0, **validated_data)
            total = 0

            # Create order items
            for item_data in items_data:
                product = item_data['product']
                quantity = item_data['quantity']
                
                # Create order item
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price # current product price
                )

                # Update stock
                product.stock_quantity -= quantity
                product.save()

                total += order_item.subtotal

            # update order total
            order.total_amount = total
            order.save()

            return order

class OrderListSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_amount', 'total_items',
            'customer_email', 'customer_phone', 'delivery_address',
            'created_at', 'updated_at', 'items'
        ]