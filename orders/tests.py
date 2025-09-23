from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
from decimal import Decimal

from catalog.models import Category, Product
from orders.models import Order, OrderItem
from orders.tasks import send_order_notifications, send_customer_sms, send_admin_email
from orders.services.order_email_service import OrderEmailService
from orders.services.order_sms_service import OrderSMSSerive

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
        
class OrderListTestCase(APITestCase):
    def setUp(self):
        # Create test users
        self.customer1 = User.objects.create_user(
            email='customer1@test.com',
            first_name='John',
            last_name='Doe',
            user_type='customer',
            phone_number='+254700000000',
            address='Test Address, Nairobi'
        )

        self.customer2 = User.objects.create_user(
            email='customer2@test.com',
            first_name='Jane',
            last_name='Doe',
            user_type='customer',
            phone_number='+254711111111',
            address='Test Address 2, Nairobi'
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

        # Create test orders
        self.order1 = Order.objects.create(
            customer=self.customer1,
            customer_phone=self.customer1.phone_number,
            customer_email=self.customer1.email,
            delivery_address=self.customer1.address,
            total_amount=Decimal('300000')
        )

        self.order2 = Order.objects.create(
            customer=self.customer2,
            customer_phone=self.customer2.phone_number,
            customer_email=self.customer2.email,
            delivery_address=self.customer2.address,
            total_amount=Decimal('500000')
        )

        # Create order items
        self.order_items = OrderItem.objects.bulk_create([
            OrderItem(
                order=self.order1, 
                product=self.product1,
                quantity=2,
                price=self.product1.price
            ),
            OrderItem(
                order=self.order2, 
                product=self.product2,
                quantity=2,
                price=self.product2.price
            )
        ])

        # Set up API client with JWT auth
        self.client = APIClient()

    def get_jwt_token(self, user):
        """Helper to get JWT token for user"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
    
    def authenticate_admin(self):
        """Authenticate as admin"""
        token = self.get_jwt_token(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_customer_can_only_access_own_orders(self):
        """User can only access their own orders"""
        token = self.get_jwt_token(self.customer1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}') 

        response = self.client.get('/api/v1/orders/', format='json')

        # Only customer1's orders should appear
        self.assertTrue(all(order['customer_email'] == self.customer1.email for order in response.data['results']))

        # Ensure customer2's order is excluded
        self.assertFalse(any(order['customer_email'] == self.customer2.email for order in response.data['results']))

    
    def test_admin_can_access_all_orders(self):
        """Admins can list all orders"""
        self.authenticate_admin()

        orders_count = Order.objects.count()

        response = self.client.get('/api/v1/orders/', format='json')

        self.assertEqual(orders_count, len(response.data['results']))

class OrderDetailTestCase(APITestCase):
    def setUp(self):
        # Create customers
        self.customer1 = User.objects.create_user(
            email="customer1@test.com",
            password="testpass123",
            user_type="customer"
        )
        self.customer2 = User.objects.create_user(
            email="customer2@test.com",
            password="testpass123",
            user_type="customer"
        )

        # Create admin
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="adminpass123",
            user_type="admin"
        )

        # Create an order for customer1
        self.order1 = Order.objects.create(
            customer=self.customer1,
            status="pending",
            total_amount=1000
        )

        # URL for order1 detail
        self.url = f"/api/v1/orders/{self.order1.id}/"

    def get_jwt_token(self, user):
        """Helper to get JWT token for user"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def authenticate_user(self, user):
        """Helper to authenticate user"""
        token = self.get_jwt_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    
    def test_customer_can_retrieve_own_order(self):
        self.authenticate_user(self.customer1)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.order1.id)

    def test_customer_cannot_retrieve_other_customer_order(self):
        self.authenticate_user(self.customer2)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_any_order(self):
        self.authenticate_user(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.order1.id)

    def test_unauthenticated_user_cannot_retrieve_order(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_nonexistent_order_returns_404(self):
        self.authenticate_user(self.customer1)

        url = "/api/v1/orders/9999/"  # assuming this ID doesn’t exist
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class OrderTasksTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.customer = User.objects.create_user(
            email='customer@test.com',
            first_name='John',
            last_name='Doe',
            user_type='customer',
            phone_number='+254700000000',
            address='Test Address'
        )
        
        self.admin = User.objects.create_user(
            email='admin@test.com',
            user_type='admin',
            is_active=True
        )

        # Create test order
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='iPhone 15',
            price=Decimal('999.99'),
            stock_quantity=10,
            category=category
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            customer_email='customer@test.com',
            customer_phone='+254700000000',
            delivery_address='Test Address',
            total_amount=Decimal('999.99')
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=product,
            quantity=1,
            price=Decimal('999.99')
        )
    
    @patch('orders.tasks.send_customer_sms.delay')
    @patch('orders.tasks.send_admin_email.delay')
    def test_send_order_notifications_success(self, mock_email, mock_sms):
        """Test successful notification orchestration"""
        # Mock the delay methods return value
        mock_email.return_value = MagicMock(id='email-task-123')
        mock_sms.return_value = MagicMock(id='sms-task-123')

        # Execute task
        result = send_order_notifications(self.order.id)

        # Assertion
        self.assertIn('sms_task_id', result)
        self.assertIn('email_task_id', result)
        self.assertEqual(result['sms_task_id'], 'sms-task-123')
        self.assertEqual(result['email_task_id'], 'email-task-123')
        
        # Verify subtasks were called with correct order ID
        mock_sms.assert_called_once_with(self.order.id)
        mock_email.assert_called_once_with(self.order.id)

    def test_send_order_notifications_order_not_found(self):
        """Test with non-existent order"""
        with self.assertRaises(Order.DoesNotExist):
            send_order_notifications(9999)

    patch('orders.tasks.order_sms_service.send_order_confirmation_sms')
    def send_customer_sms_success(self, mock_sms_service):
        """Test successful sms sending"""
        mock_sms_service.return_value = {'success': True, 'message_id': 'test-123', 'cost': 'KES 1.00'}

        result = send_customer_sms(self.order.id)

        self.assertIn('message_id', result)
        self.assertTrue(result['success'])
        mock_sms_service.assert_called_once_with(self.order.id)

    patch('orders.tasks.order_sms_service.send_order_confirmation_sms')
    def send_customer_sms_no_phone_number(self, mock_sms_service):
        """Test SMS task when customer has no phone number"""
        order_no_phone = Order.objects.create(
            customer=self.customer,
            customer_email='customer@test.com',
            customer_phone='',  # Empty phone
            delivery_address='Test Address',
            total_amount=Decimal('999.99')
        )

        result = send_customer_sms(order_no_phone.id)

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No phone number')
        mock_sms_service.assert_not_called()

    def test_send_customer_sms_order_not_found(self):
        """Test SMS task with non-existent order"""
        with self.assertRaises(Order.DoesNotExist):
            send_customer_sms(99999)

    @patch('orders.tasks.order_sms_service.send_order_confirmation_sms')
    def test_send_customer_sms_service_failure(self, mock_sms_service):
        """Test SMS task when service raises exception"""
        # Mock service to raise exception
        mock_sms_service.side_effect = Exception("Africa's Talking API error")
        
        with self.assertRaises(Exception) as context:
            send_customer_sms(self.order.id)
        
        self.assertIn("Africa's Talking API error", str(context.exception))

    @patch('orders.tasks.order_email_service.send_admin_notification')
    def test_send_admin_email_success(self, mock_email_service):
        """Test successful admin email sending"""
        # Mock service response
        mock_email_service.return_value = {
            'success': True,
            'recipients': 1,
            'admin_emails': ['admin@test.com']
        }
        
        # Execute task
        result = send_admin_email(self.order.id)
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(result['recipients'], 1)
        self.assertIn('admin@test.com', result['admin_emails'])
        
        # Verify service was called with correct order
        mock_email_service.assert_called_once_with(self.order)

    def test_send_admin_email_order_not_found(self):
        """Test admin email task with non-existent order"""
        with self.assertRaises(Order.DoesNotExist):
            send_admin_email(99999)

    @patch('orders.tasks.order_email_service.send_admin_notification')
    def test_send_admin_email_service_failure(self, mock_email_service):
        """Test admin email task when service fails"""
        # Mock service to raise exception
        mock_email_service.side_effect = Exception("SMTP server unavailable")
        
        with self.assertRaises(Exception) as context:
            send_admin_email(self.order.id)
        
        self.assertIn("SMTP server unavailable", str(context.exception))

class OrderEmailServiceTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.customer = User.objects.create_user(
            email='customer@test.com',
            first_name='John',
            last_name='Doe',
            user_type='customer'
        )
        
        self.admin1 = User.objects.create_user(
            email='admin1@test.com',
            first_name='Admin',
            last_name='One',
            user_type='admin',
            is_active=True
        )
        
        self.admin2 = User.objects.create_user(
            email='admin2@test.com',
            first_name='Admin',
            last_name='Two',
            user_type='admin',
            is_active=True
        )
        
        # Create inactive admin (should be excluded)
        self.inactive_admin = User.objects.create_user(
            email='inactive@test.com',
            user_type='admin',
            is_active=False
        )

        # Create test order with items
        category = Category.objects.create(name='Electronics')
        self.product1 = Product.objects.create(
            name='iPhone 15',
            price=Decimal('999.99'),
            category=category
        )
        self.product2 = Product.objects.create(
            name='MacBook Pro',
            price=Decimal('1999.99'),
            category=category
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            customer_email='customer@test.com',
            customer_phone='+254700000000',
            delivery_address='123 Test Street, Nairobi',
            total_amount=Decimal('2999.97')
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=1,
            price=Decimal('999.99')
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            quantity=1,
            price=Decimal('1999.99')
        )
        
        self.service = OrderEmailService()

    def test_get_admin_emails_success(self):
        """Test retrieving active admin emails"""
        admin_emails = self.service.get_admin_emails()

        # Should return 2 active admins
        self.assertEqual(len(admin_emails), 2)
        self.assertIn('admin1@test.com', admin_emails)
        self.assertIn('admin2@test.com', admin_emails)

        # should not include inactive admins and customer email
        self.assertNotIn('inactive@test.com', admin_emails)
        self.assertNotIn('customer@test.com', admin_emails)

    def test_get_admin_emails_no_admins(self):
        """Test retrieving admin emails when no active admins exist"""
        # Delete all active admins
        User.objects.filter(user_type='admin', is_active=True).delete()
        
        admin_emails = self.service.get_admin_emails()
        
        self.assertEqual(len(admin_emails), 0)
        self.assertEqual(admin_emails, [])

    def test_create_admin_notification_content(self):
        """Test creating email subject and message content"""
        subject, message = self.service.create_admin_notification_content(self.order)
        
        # Test subject
        expected_subject = f'New Order #{self.order.id} - $2999.97'
        self.assertEqual(subject, expected_subject)
        
        # Test message content contains key information
        self.assertIn(f'Order ID: #{self.order.id}', message)
        self.assertIn('Customer: John Doe', message)
        self.assertIn('customer@test.com', message)
        self.assertIn('+254700000000', message)
        self.assertIn('$2999.97', message)
        self.assertIn('123 Test Street, Nairobi', message)
        self.assertIn('iPhone 15 x 1 = $999.99', message)
        self.assertIn('MacBook Pro x 1 = $1999.99', message)
        self.assertIn('Items: 2', message)
    
    def test_send_admin_notification_success(self):
        """Test successful admin notification sending"""
        # Clear any existing emails
        mail.outbox = []
        
        result = self.service.send_admin_notification(self.order)
        
        # Check return value
        self.assertTrue(result['success'])
        self.assertEqual(result['recipients'], 2)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email content
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, f'New Order #{self.order.id} - $2999.97')
        self.assertEqual(len(sent_email.to), 2)
        self.assertIn('admin1@test.com', sent_email.to)
        self.assertIn('admin2@test.com', sent_email.to)
        self.assertIn('iPhone 15', sent_email.body)
        self.assertIn('MacBook Pro', sent_email.body)

    def test_send_admin_notification_no_admins(self):
        """Test sending notification when no admins exist"""
        # Delete all admins
        User.objects.filter(user_type='admin').delete()
        
        result = self.service.send_admin_notification(self.order)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No admin emails')

    @patch('orders.services.order_email_service.send_mail')
    def test_send_admin_notification_email_failure(self, mock_send_mail):
        """Test handling email sending failure"""
        # Mock send_mail to raise exception
        mock_send_mail.side_effect = Exception("SMTP server unavailable")
        
        result = self.service.send_admin_notification(self.order)
        
        self.assertFalse(result['success'])
        self.assertIn('Email sending failed', result['error'])
        self.assertIn('SMTP server unavailable', result['error'])

    @patch("orders.services.order_email_service.send_mail")
    def test_send_admin_notification_send_mail_called_correctly(self, mock_send_mail):
        """Test that send_mail is called with correct parameters"""
        mock_send_mail.return_value = True
        
        self.service.send_admin_notification(self.order)
        
        # Verify send_mail was called
        mock_send_mail.assert_called_once()
        
        # Get the call arguments
        call_args = mock_send_mail.call_args
        
        # Check arguments
        self.assertEqual(call_args.kwargs['subject'], f'New Order #{self.order.id} - $2999.97')
        self.assertIn('iPhone 15', call_args.kwargs['message'])
        self.assertEqual(len(call_args.kwargs['recipient_list']), 2)
        self.assertIn('admin1@test.com', call_args.kwargs['recipient_list'])
        self.assertIn('admin2@test.com', call_args.kwargs['recipient_list'])
        self.assertFalse(call_args.kwargs['fail_silently'])

class OrderSMSService(TestCase):
    def setUp(self):
        """Set up test data"""
        self.customer = User.objects.create_user(
            email='customer@test.com',
            first_name='John',
            last_name='Doe',
            user_type='customer'
        )
        
        # Create test order
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='iPhone 15',
            price=Decimal('999.99'),
            category=category
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            customer_email='customer@test.com',
            customer_phone='+254700123456',
            delivery_address='Test Address',
            total_amount=Decimal('999.99')
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=product,
            quantity=1,
            price=Decimal('999.99')
        )
        
        self.service = OrderSMSSerive()

    def test_format_phone_number_already_formatted(self):
        """Test formatting phone number that's already in correct format"""
        phone = '+254700123456'
        formatted = self.service.format_phone_number(phone)
        self.assertEqual(formatted, '+254700123456')

    def test_format_phone_number_starts_with_254(self):
        """Test formatting phone number starting with 254"""
        phone = '254700123456'
        formatted = self.service.format_phone_number(phone)
        self.assertEqual(formatted, '+254700123456')

    def test_format_phone_number_starts_with_zero(self):
        """Test formatting phone number starting with 0"""
        phone = '0700123456'
        formatted = self.service.format_phone_number(phone)
        self.assertEqual(formatted, '+254700123456')

    def test_format_phone_number_starts_with_seven(self):
        """Test formatting phone number starting with 7"""
        phone = '700123456'
        formatted = self.service.format_phone_number(phone)
        self.assertEqual(formatted, '+254700123456')

    def test_format_phone_number_starts_with_one(self):
        """Test formatting phone number starting with 1"""
        phone = '100123456'
        formatted = self.service.format_phone_number(phone)
        self.assertEqual(formatted, '+254100123456')

    def test_create_order_confirmation_message(self):
        """Test creating order confirmation SMS message"""
        message = self.service.create_order_confirmation_message(self.order)
        
        expected_message = (
            f"Hi John! "
            f"Your order #{self.order.id} for $999.99 has been confirmed. "
            f"We'll notify you when it's ready for delivery. Thank you!"
        )
        
        self.assertEqual(message, expected_message)
        self.assertIn('John', message)
        self.assertIn(str(self.order.id), message)
        self.assertIn('999.99', message)

    def test_send_order_confirmation_sms_no_phone_number(self):
        """Test sending SMS when order has no phone number"""
        # Create order without phone number
        order_no_phone = Order.objects.create(
            customer=self.customer,
            customer_email='customer@test.com',
            customer_phone='',  # Empty phone
            delivery_address='Test Address',
            total_amount=Decimal('999.99')
        )
        
        result = self.service.send_order_confirmation_sms(order_no_phone)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No phone number')

    @patch('orders.services.order_sms_service.SMSService')
    def test_send_order_confirmation_sms_success(self, mock_sms_service):
        """Test successful SMS sending"""
        # Mock the SMS client
        mock_client = MagicMock()
        mock_sms_service.return_value = mock_client
        
        # Mock successful API response
        mock_response = {
            'SMSMessageData': {
                'Recipients': [{
                    'status': 'Success',
                    'messageId': 'ATXid_123456789',
                    'cost': 'KES 2.00',
                    'statusCode': '101'
                }]
            }
        }
        mock_client.send.return_value = mock_response
        
        # Create new service instance to get mocked SMS client
        service = OrderSMSSerive()
        result = service.send_order_confirmation_sms(self.order)
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(result['phone'], '+254700123456')
        self.assertEqual(result['message_id'], 'ATXid_123456789')
        self.assertEqual(result['cost'], 'KES 2.00')
        self.assertEqual(result['status'], 'Success')
        self.assertIn('John', result['message'])

    @patch('orders.services.order_sms_service.SMSService')
    def test_send_order_confirmation_sms_api_failure(self, mock_sms_service):
        """Test SMS sending when API returns failure status"""
        # Mock the SMS client
        mock_client = MagicMock()
        mock_sms_service.return_value = mock_client
        
        # Mock failure API response
        mock_response = {
            'SMSMessageData': {
                'Recipients': [{
                    'status': 'Failed',
                    'statusCode': '103'
                }]
            }
        }
        mock_client.send.return_value = mock_response
        
        service = OrderSMSSerive()
        result = service.send_order_confirmation_sms(self.order)
        
        # Assertions
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Failed')
        self.assertEqual(result['phone'], '+254700123456')
        self.assertEqual(result['status_code'], '103')

    @patch('orders.services.order_sms_service.SMSService')
    def test_send_order_confirmation_sms_exception(self, mock_sms_service):
        """Test SMS sending when exception occurs"""
        # Mock the SMS client to raise exception
        mock_client = MagicMock()
        mock_sms_service.return_value = mock_client
        mock_client.send.side_effect = Exception("Network error")
        
        service = OrderSMSSerive()
        result = service.send_order_confirmation_sms(self.order)
        
        # Assertions
        self.assertFalse(result['success'])
        self.assertIn('SMS sending failed', result['error'])
        self.assertIn('Network error', result['error'])
        self.assertEqual(result['phone'], '+254700123456')

    def test_process_sms_response_success(self):
        """Test processing successful SMS response"""
        response = {
            'SMSMessageData': {
                'Recipients': [{
                    'status': 'Success',
                    'messageId': 'ATXid_123456789',
                    'cost': 'KES 2.00',
                    'statusCode': '101'
                }]
            }
        }
        
        result = self.service._process_sms_response(response, '+254700123456', 'Test message')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['phone'], '+254700123456')
        self.assertEqual(result['message'], 'Test message')
        self.assertEqual(result['message_id'], 'ATXid_123456789')
        self.assertEqual(result['cost'], 'KES 2.00')
        self.assertEqual(result['status'], 'Success')

    def test_process_sms_response_failure(self):
        """Test processing failed SMS response"""
        response = {
            'SMSMessageData': {
                'Recipients': [{
                    'status': 'Failed',
                    'statusCode': '103'
                }]
            }
        }
        
        result = self.service._process_sms_response(response, '+254700123456', 'Test message')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Failed')
        self.assertEqual(result['phone'], '+254700123456')
        self.assertEqual(result['status_code'], '103')

    def test_process_sms_response_empty_recipients_array(self):
        """Test processing response with empty recipients array"""
        response = {
            'SMSMessageData': {
                'Recipients': []
            }
        }
        
        result = self.service._process_sms_response(response, '+254700123456', 'Test message')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No recipients found in API response')
        self.assertEqual(result['phone'], '+254700123456')