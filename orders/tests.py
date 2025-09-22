from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
from decimal import Decimal

from catalog.models import Category, Product
from orders.models import Order, OrderItem

User = get_user_model()

class OrderCreationTestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.customer = User.objects.create_user(
            email='customer@test.com',
            first_name='John',
            last_name='Doe',
            user_type='customer',
            phone_number='+254700000000',
            address='Test Address, Nairobi'
        )

        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            user_type='admin',
        )

        # Create test products
        self.category = Category.objects.create(name='Electronics')
        self.product1 = Product.objects.create(
            name='Samsung S25',
            price=Decimal('150000.00'),
            stock_quantity=10,
            category=self.category
        )
        self.product2 = Product.objects.create(
            name='Macbook Pro',
            price=Decimal('250000.00'),
            stock_quantity=5,
            category=self.category
        )

        # Set up API client with JWT auth
        self.client = APIClient()

    def get_jwt_token(self, user):
        """Helper to get JWT token for user"""
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

    @patch('orders.tasks.send_order_notifications.delay') # mock the task function
    def test_create_order_success(self, mock_notifications): # mock_notifications is automatically injected here
        """Test successful order creation with complete user profile"""
        self.authenticate_customer()

        order_data = {
            'items': [
                {'product': self.product1.id, 'quantity': 2},
                {'product': self.product2.id, 'quantity': 1},
            ]
        }

        response = self.client.post(path='/api/v1/orders/', data=order_data, format='json')

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check order was created
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()

        # Check order details
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.total_amount, Decimal('550000.00'))
        self.assertEqual(order.customer_email, 'customer@test.com')
        self.assertEqual(order.customer_phone, '+254700000000')
        self.assertEqual(order.delivery_address, 'Test Address, Nairobi')

        # Check order items
        self.assertEqual(OrderItem.objects.count(), 2)

        # Check stock was updated
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 8) # 10 - 2
        self.assertEqual(self.product2.stock_quantity, 4) # 5 - 1

        # Check notifications were triggered with correct order id
        mock_notifications.assert_called_once()
        call_args = mock_notifications.call_args[0][0]
        self.assertEqual(call_args, order.id)

    def test_create_order_insufficient_stock(self):
        """Test order creation with insufficient stock"""
        self.authenticate_customer()

        order_data = {
            'items': [
                {'product': self.product1.id, 'quantity': 100} # More than available quantity
            ]
        }

        response = self.client.post(path='/api/v1/orders/', data=order_data, format='json')

        # Should fail with validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient stock', str(response.data))

        # No order should be created
        self.assertEqual(Order.objects.count(), 0)

        # Stock should remain unchanged
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock_quantity, 10)

    def test_create_order_zero_quantity(self):
        self.authenticate_customer()

        order_data = {
            'items': [
                {'product': self.product1.id, 'quantity': 0}
            ]
        }

        response = self.client.post(path='/api/v1/orders/', data=order_data, format='json')

        # shoudl fail with validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Quantity must be greater than 0', str(response.data))

        # No order should be created
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_zero_items(self):
        self.authenticate_customer()

        order_data = {
            'items': []
        }

        response = self.client.post(path='/api/v1/orders/', data=order_data, format='json')

        # shoudl fail with validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Order must have at least one item', str(response.data))

        # No order should be created
        self.assertEqual(Order.objects.count(), 0)

    def test_order_create_incomplete_profile(self):
        """Test order creation with incomplete customer profile"""
        # Create customer without phone and address
        incomplete_customer = User.objects.create_user(
            email='incomplete@test.com',
            user_type='customer',
            first_name='Incomplete',
            last_name='User'
        )

        token = self.get_jwt_token(incomplete_customer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        order_data = {
            'items': [
                {'product': self.product1.id, 'quantity': 1}
            ]
        }

        response = self.client.post('/api/v1/orders/', order_data, format='json')
        
        # Should fail with validation errors
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('customer_phone', str(response.data))
        self.assertIn('delivery_address', str(response.data))

    @patch('orders.tasks.send_order_notifications.delay')
    def test_create_order_with_provided_details(self, mock_notifications):
        """Test order creation with customer providing details at checkout"""
        self.authenticate_customer()

        order_data = {
            'customer_phone': '+254711111111',  # Different from profile
            'delivery_address': 'Gift delivery: Office Building',  # Different from profile
            'save_as_default': False,
            'items': [{'product': self.product1.id, 'quantity': 1}]
        }

        response = self.client.post('/api/v1/orders/', order_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = Order.objects.first()

        # Order should have provided details. not profile details
        self.assertEqual(order.customer_phone, '+254711111111')
        self.assertEqual(order.delivery_address, 'Gift delivery: Office Building')

        # Profile should remain unchanged as save_as_default=False
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone_number, '+254700000000')
        self.assertEqual(self.customer.address, 'Test Address, Nairobi')

    @patch('orders.tasks.send_order_notifications.delay')
    def test_create_order_save_as_default(self, mock_notifications):
        """Test order creation with save_as_default=True updates profile"""
        self.authenticate_customer()
        
        order_data = {
            'customer_phone': '+254722222222',
            'delivery_address': 'New Default Address',
            'save_as_default': True,
            'items': [{'product': self.product1.id, 'quantity': 1}]
        }
        
        response = self.client.post('/api/v1/orders/', order_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Profile should be updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.phone_number, '+254722222222')
        self.assertEqual(self.customer.address, 'New Default Address')

    def test_admin_cannot_create_order(self):
        """Test that admins cannot create orders"""
        self.authenticate_admin()
        
        order_data = {
            'items': [{'product': self.product1.id, 'quantity': 1}]
        }
        
        response = self.client.post('/api/v1/orders/', order_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Order.objects.count(), 0)

    def test_unauthenticated_cannot_create_order(self):
        """Test that unauthenticated users cannot create orders"""
        order_data = {
            'items': [{'product': self.product1.id, 'quantity': 1}]
        }
        
        response = self.client.post('/api/v1/orders/', order_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Order.objects.count(), 0)
        