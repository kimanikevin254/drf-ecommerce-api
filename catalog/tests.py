from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from decimal import Decimal

from catalog.models import Category, Product

User = get_user_model()

class CategoryModelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.root_category = Category.objects.create(name='Electronics')
        self.sub_category = Category.objects.create(
            name='Mobile Phones',
            parent=self.root_category
        )
        self.sub_sub_category = Category.objects.create(
            name='Smartphones',
            parent=self.sub_category
        )

    def test_category_str_representation(self):
        """Test category string representation"""
        self.assertEqual(str(self.root_category), 'Electronics')

    def test_get_full_path_root_category(self):
        """Test full path for root category"""
        self.assertEqual(self.root_category.get_full_path(), 'Electronics')

    def test_get_full_path_nested_category(self):
        """Test full path for nested category"""
        expected_path = 'Electronics > Mobile Phones > Smartphones'
        self.assertEqual(self.sub_sub_category.get_full_path(), expected_path)

    def test_get_all_children_with_nested_structure(self):
        """Test getting all children recursively"""
        children = self.root_category.get_all_children()
        
        self.assertEqual(len(children), 2)
        self.assertIn(self.sub_category, children)
        self.assertIn(self.sub_sub_category, children)

    def test_get_all_children_leaf_category(self):
        """Test getting children of leaf category"""
        children = self.sub_sub_category.get_all_children()
        self.assertEqual(len(children), 0)

class ProductModelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='iPhone 15',
            description='Latest iPhone model',
            price=Decimal('999.99'),
            category=self.category,
            stock_quantity=10
        )

    def test_product_str_representation(self):
        """Test product string representation"""
        expected = 'iPhone 15 - $999.99'
        self.assertEqual(str(self.product), expected)

    def test_product_default_values(self):
        """Test product default field values"""
        self.assertTrue(self.product.is_active)
        self.assertIsNotNone(self.product.created_at)
        self.assertIsNotNone(self.product.updated_at)

class CategoryAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data and authentication"""
        # Create users
        self.customer = User.objects.create_user(
            email='customer@test.com',
            password='testpass123',
            user_type='customer'
        )
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='admin',
            is_staff=True
        )
        
        # Create test categories
        self.parent_category = Category.objects.create(name='Electronics')
        self.child_category = Category.objects.create(
            name='Smartphones',
            parent=self.parent_category
        )
        
        # Create products for testing
        Product.objects.create(
            name='iPhone 15',
            price=Decimal('999.99'),
            category=self.child_category,
            stock_quantity=5
        )
        Product.objects.create(
            name='Samsung Galaxy',
            price=Decimal('799.99'),
            category=self.child_category,
            stock_quantity=3
        )

    def get_jwt_token(self, user):
        """Helper to get JWT token"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def authenticate_customer(self):
        """Authenticate as customer"""
        token = self.get_jwt_token(self.customer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def authenticate_admin(self):
        """Authenticate as admin"""
        token = self.get_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_list_categories_unauthenticated(self):
        """Test listing categories without authentication (should work)"""
        response = self.client.get('/api/v1/catalog/categories/')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['data']['results']), 2)

    def test_list_categories_authenticated(self):
        """Test listing categories with authentication"""
        self.authenticate_customer()
        response = self.client.get('/api/v1/catalog/categories/')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['data']['results']), 2)

    def test_create_category_as_admin(self):
        """Test creating category as admin (should succeed)"""
        self.authenticate_admin()
        
        category_data = {
            'name': 'Laptops',
            'parent': self.parent_category.id
        }
        
        response = self.client.post('/api/v1/catalog/categories/', category_data)
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(data['data']['name'], 'Laptops')
        
        # Verify category was created
        self.assertTrue(Category.objects.filter(name='Laptops').exists())

    def test_create_category_as_customer(self):
        """Test creating category as customer (should fail)"""
        self.authenticate_customer()
        
        category_data = {
            'name': 'Tablets',
            'parent': self.parent_category.id
        }
        
        response = self.client.post('/api/v1/catalog/categories/', category_data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_category_unauthenticated(self):
        """Test creating category without authentication (should fail)"""
        category_data = {
            'name': 'Tablets'
        }
        
        response = self.client.post('/api/v1/catalog/categories/', category_data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_category_as_admin(self):
        """Test updating category as admin"""
        self.authenticate_admin()
        
        update_data = {
            'name': 'Smart Devices'
        }
        
        response = self.client.patch(
            f'/api/v1/catalog/categories/{self.child_category.id}/',
            update_data
        )
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['data']['name'], 'Smart Devices')
        
    def test_delete_category_with_products_should_fail(self):
        """Test deleting category that has products (should fail)"""
        self.authenticate_admin()
        
        response = self.client.delete(
            f'/api/v1/catalog/categories/{self.child_category.id}/'
        )
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot delete a category with products. Move or delete products first.', data['errors'])

    def test_category_average_price_endpoint(self):
        """Test category average price calculation"""
        response = self.client.get(
            f'/api/v1/catalog/categories/{self.child_category.id}/average-price/'
        )
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(data['success'])
        
        # Average of 999.99 and 799.99 = 899.99
        expected_avg = 899.99
        self.assertEqual(data['data']['average_price'], expected_avg)
        self.assertEqual(data['data']['total_products'], 2)

    def test_category_average_price_nonexistent_category(self):
        """Test average price for non-existent category"""
        response = self.client.get('/api/v1/catalog/categories/99999/average-price/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class ProductAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        # Create users
        self.customer = User.objects.create_user(
            email='customer@test.com',
            password='testpass123',
            user_type='customer'
        )
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            user_type='admin',
            is_staff=True
        )
        
        # Create test data
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='iPhone 15',
            description='Latest iPhone',
            price=Decimal('999.99'),
            category=self.category,
            stock_quantity=10
        )

    def get_jwt_token(self, user):
        """Helper to get JWT token"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def authenticate_customer(self):
        """Authenticate as customer"""
        token = self.get_jwt_token(self.customer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def authenticate_admin(self):
        """Authenticate as admin"""
        token = self.get_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_list_products_unauthenticated(self):
        """Test listing products without authentication"""
        response = self.client.get('/api/v1/catalog/products/')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['data']['results']), 1)

    def test_create_product_as_admin(self):
        """Test creating product as admin"""
        self.authenticate_admin()
        
        product_data = {
            'name': 'MacBook Pro',
            'description': 'Professional laptop',
            'price': '1999.99',
            'category': self.category.id,
            'stock_quantity': 5
        }
        
        response = self.client.post('/api/v1/catalog/products/', product_data)
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['name'], 'MacBook Pro')

    def test_create_product_as_customer(self):
        """Test creating product as customer (should fail)"""
        self.authenticate_customer()
        
        product_data = {
            'name': 'iPad',
            'price': '599.99',
            'category': self.category.id
        }
        
        response = self.client.post('/api/v1/catalog/products/', product_data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_product_invalid_price(self):
        """Test creating product with invalid price"""
        self.authenticate_admin()
        
        product_data = {
            'name': 'Invalid Product',
            'price': '-100.00',  # Negative price
            'category': self.category.id
        }
        
        response = self.client.post('/api/v1/catalog/products/', product_data)
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Price must be greater than 0', data['errors']['price'])

    def test_create_product_invalid_stock(self):
        """Test creating product with invalid stock quantity"""
        self.authenticate_admin()
        
        product_data = {
            'name': 'Invalid Product',
            'price': '100.00',
            'category': self.category.id,
            'stock_quantity': -5  # Negative stock
        }
        
        response = self.client.post('/api/v1/catalog/products/', product_data)
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Ensure this value is greater than or equal to 0.', data['errors']['stock_quantity'])

    def test_update_product_as_admin(self):
        """Test updating product as admin"""
        self.authenticate_admin()
        
        update_data = {
            'name': 'iPhone 15 Pro',
            'price': '1099.99'
        }
        
        response = self.client.patch(
            f'/api/v1/catalog/products/{self.product.id}/',
            update_data
        )
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['data']['name'], 'iPhone 15 Pro')
        self.assertEqual(data['data']['price'], '1099.99')

    def test_soft_delete_product(self):
        """Test soft deleting product (should mark as inactive)"""
        self.authenticate_admin()
        
        response = self.client.delete(f'/api/v1/catalog/products/{self.product.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Product should still exist but be inactive
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)

    def test_product_filtering_by_category(self):
        """Test filtering products by category"""
        response = self.client.get(
            f'/api/v1/catalog/products/?category={self.category.id}'
        )
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['data']['results']), 1)

    def test_product_search(self):
        """Test searching products by name"""
        response = self.client.get('/api/v1/catalog/products/?search=iPhone')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['data']['results']), 1)
        self.assertIn('iPhone', data['data']['results'][0]['name'])

    def test_product_ordering_by_price(self):
        """Test ordering products by price"""
        # Create another product
        Product.objects.create(
            name='Cheap Phone',
            price=Decimal('199.99'),
            category=self.category,
            stock_quantity=5
        )
        
        response = self.client.get('/api/v1/catalog/products/?ordering=price')
        data = response.json()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data['data']['results']), 2)
        
        # First product should be the cheaper one
        self.assertEqual(data['data']['results'][0]['name'], 'Cheap Phone')