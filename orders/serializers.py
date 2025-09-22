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

    save_as_default = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Order
        fields = [
            'customer_email', 'customer_phone', 'delivery_address',
            'items', 'total_amount', 'save_as_default'
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
            
        # Validate required fields for order completion
        user = self.context['request'].user

        final_phone = data.get('customer_phone') or user.phone_number
        final_address = data.get('delivery_address') or user.address

        errors = {}

        if not final_phone:
            errors['customer_phone'] = 'Phone number is required for SMS notifications and delivery. Please provide one.'
        
        if not final_address:
            errors['delivery_address'] = 'Delivery address is required. Please provide one.'
        
        if errors:
            raise serializers.ValidationError(errors)
        
        # Store final values for use in the create method
        data['_final_phone'] = final_phone  
        data['_final_address'] = final_address
        data['_save_as_default'] = data.pop('save_as_default', False)
            
        return data

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                'Order must have at least one item'
            )
        return value
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        
        save_as_default = validated_data.pop('_save_as_default', False)
        final_phone = validated_data.pop('_final_phone')
        final_address = validated_data.pop('_final_address')

        user = self.context['request'].user
        
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

            # Update user delivery_address/phone_number is requested
            profile_updated = False
            if save_as_default:
                # Only update if provided values are different from the saved ones
                if final_phone != user.phone_number:
                    user.phone_number = final_phone
                    profile_updated = True
                
                if final_address != user.address:
                    user.address = final_address
                    profile_updated = True

                if profile_updated:
                    user.save()

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