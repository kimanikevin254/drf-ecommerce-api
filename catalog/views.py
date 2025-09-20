from rest_framework import generics, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

class CategoryListCreateAPIView(generics.ListCreateAPIView):
    """
    List or create a new category
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a category
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def destroy(self, request, *args, **kwargs):
        """Custom destroy method with additional checks"""
        category = self.get_object()

        # Check if category has children
        if category.children.exists():
            return Response(
                data='Cannot delete a category with subcategories. Delete subcategories first.',
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if category has products
        if category.products.exists():
            return Response(
                data='Cannot delete a category with products. Move or delete products first.',
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)
    
class ProductListCreateAPIView(generics.ListCreateAPIView):
    """
    List all products or create a new product
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'category__parent']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a product
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def perform_destroy(self, instance):
        """Soft delete - mark as inactive instead of deleting"""
        instance.is_active = False
        instance.save()