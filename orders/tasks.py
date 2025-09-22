import logging

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Order

User = get_user_model()
logger = logging.getLogger(__name__)

@shared_task
def send_order_notifications(order_id):
    """
    Send SMS to customer and email to admins when order is placed
    """
    try:
        order = Order.objects.get(id=order_id)

        # Send SMS to customer
        sms_result = send_customer_sms.delay(order.id)
        
        # Send email to admins
        email_result = send_admin_email.delay(order.id)
        
        logger.info(f"Notification tasks queued for order {order.id}")
        return {
            'sms_task_id': sms_result.id,
            'email_task_id': email_result.id
        }
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        raise


@shared_task
def send_customer_sms(order_id):
    """"
    Send SMS notifications to customer using Africa's talking
    """
    try:
        order = Order.objects.get(id=order_id)

        if not order.customer_phone:
            logger.warning(f'No phone number for order {order.id}')
            return {'success': False, 'error': 'No phone number'}
        
        message = (
            f"Hi {order.customer.first_name}! "
            f"Your order #{order.id} for ${order.total_amount} has been confirmed. "
            f"We'll notify you when it's ready for delivery. Thank you!"
        )

        # TODO: Implement Africa's Talking API call
        logger.infp(f'SMS to {order.customer_phone}: {message}')

        return {
            'success': True,
            'phone': order.customer_phone,
            'message': message
        }
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        raise

@shared_task
def send_admin_email(order_id):
    try:
        """
        Send email notification to admins about the new order
        """
        order = order = Order.objects.get(id=order_id)

        # Get all admin users
        admin_emails = User.objects.filter(
            user_type='admin',
            is_active=True
        ).values_list('email', flat=True)

        if not admin_emails:
            logger.warning('No admin emails found')
            return {'success': False, 'error': 'No admin emails'}
        
        # Prepare order details
        order_items = []
        for item in order.items.all():
            order_items.append(
                f'- {item.product.name} x {item.quantity} = ${item.subtotal}'
            )

        subject = f'New Order #{order.id} - ${order.total_amount}'
        messsage = f"""
New order has been placed!

Order Details:
- Order ID: #{order.id}
- Customer: {order.customer.first_name} {order.customer.last_name}
- Email: {order.customer_email}
- Phone: {order.customer_phone}
- Total Amount: ${order.total_amount}
- Items: {order.total_items}

Items Ordered:
{chr(10).join(order_items)}

Delivery Address:
{order.delivery_address}

Order placed at: {order.created_at}

Please process this order promptly.
        """
    
        # Send email to all admins
        send_mail(
            subject=subject,
            message=messsage,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(admin_emails),
            fail_silently=False
        )

        logger.info(f"Admin email sent for order {order.id} to {len(admin_emails)} admins")
            
        return {
            'success': True,
            'recipients': len(admin_emails),
            'admin_emails': list(admin_emails)
        }
    
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        raise
    
    except Exception as e:
        logger.error(f"Failed to send admin email for order {order.id}: {str(e)}")
        raise