from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.StringRelatedField(many=True, read_only=True)
    full_path = serializers.ReadOnlyField(source='get_full_path')
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'children', 'full_path']

    def validate_parent(self, value):
        """
        Prevent circular references
        """
        if not value or not self.instance:
            return value

        # Check if new value is a descendant of this category
        if value in self.instance.get_all_children():
            raise serializers.ValidationError(
                'Cannot set parent as this would cause circular reference'
            )
        
        # Prevent self reference
        if value.pk == self.instance.pk:
            raise serializers.ValidationError(
                'A category cannot be its own parent'
            )
        
        return value
    
class ProductCategorySerializer(serializers.ModelSerializer):
    full_path = serializers.ReadOnlyField(source='get_full_path')

    class Meta:
        model = Category
        fields = ['id', 'name', 'full_path']
    
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'category',
            'stock_quantity', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['category'] = ProductCategorySerializer(instance.category).data # replace with detailed data
        return data

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than 0')
        return value
    
    def validate_stock_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Stock quantity cannot be negative')
        return value