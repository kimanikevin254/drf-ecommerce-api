from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'get_full_path', 'created_at']
    list_filter = ['created_at', 'parent']
    search_fields = ['name']
    ordering = ['name']
    
    # Show hierarchy in a tree-like structure
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'stock_quantity', 'is_active']
    ordering = ['-created_at']
    
    # Add filtering by category hierarchy
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')