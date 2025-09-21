from rest_framework import generics, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .permissions import IsAdminOrReadOnly

class CategoryListCreateAPIView(generics.ListCreateAPIView):
    """
    List or create a new category
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a category
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

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
    
class CategoryAveragePriceAPIView(APIView):
    """
    Return average product price for a given category
    """
    def get(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response(
                data='Category with the given ID does not exist',
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get all products in this category and subcategories
        all_categories = [category] + category.get_all_children()
        
        avg_price = Product.objects.filter(
            category__in=all_categories,
            is_active = True
        ).aggregate( # perform db-level calculation
            avg_price=Avg('price') # get average of the proce field
        )['avg_price'] # extract the value from returned dict

        total_products = Product.objects.filter(
            category__in=all_categories,
            is_active = True
        ).count()

        return Response(
            data={
                'category_id': category.id,
                'category_name': category.name,
                'average_price': round(avg_price, 2) if avg_price else 0,
                'total_products': total_products
            },
            status=status.HTTP_200_OK
        )
    
class ProductListCreateAPIView(generics.ListCreateAPIView):
    """
    List all products or create a new product
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
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
    permission_classes = [IsAdminOrReadOnly]

    def perform_destroy(self, instance):
        """Soft delete - mark as inactive instead of deleting"""
        instance.is_active = False
        instance.save()