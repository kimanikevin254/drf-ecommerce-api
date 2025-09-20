from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.StringRelatedField(many=True, read_only=True)
    full_path = serializers.ReadOnlyField()
    
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