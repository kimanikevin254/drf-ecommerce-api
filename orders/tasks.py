import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Order
from .services import order_sms_service, order_email_service

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
        
        # Send SMS via Africa's Talking API
        result = order_sms_service.send_order_confirmation_sms(order)

        return result
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        raise
    except Exception as e:
        logger.error(f"Failed to send customer SMS for order #{order.id}: {str(e)}")
        raise

@shared_task
def send_admin_email(order_id):
    try:
        """
        Send email notification to admins about the new order
        """
        order = Order.objects.get(id=order_id)

        result = order_email_service.send_admin_notification(order)

        logger.info(f"Admin email sent for order {order.id} to {result['recipients']} admins")
            
        return result
    
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        raise
    
    except Exception as e:
        logger.error(f"Failed to send admin email for order {order.id}: {str(e)}")
        raise