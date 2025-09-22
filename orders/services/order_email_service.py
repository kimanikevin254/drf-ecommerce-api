import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

User = get_user_model()
logger = logging.getLogger(__name__)

class OrderEmailService:
    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def get_admin_emails(self):
        """Get list of active admin emails"""
        admin_emails = User.objects.filter(
            user_type='admin',
            is_active=True
        ).values_list('email', flat=True)

        return list(admin_emails)
    
    def create_admin_notification_content(self, order):
        """Create subject and message content for admin notification"""
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

        return subject, messsage
    
    def send_admin_notification(self, order):
        """Send email notification to all active admins"""
        try:
            admin_emails = self.get_admin_emails()

            if not admin_emails:
                logger.warning('No admin emails found')
                return {'success': False, 'error': 'No admin emails'}
            
            subject, message = self.create_admin_notification_content(order)

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False
            )

            logger.info(f"Admin email sent for order {order.id} to {len(admin_emails)} admins")

            return {
                'success': True,
                'recipients': len(admin_emails)
            }
        
        except Exception as e:
            logger.error(f"Failed to send admin notification for order {order.id}: {str(e)}")
            return {
                'success': False,
                'error': f'Email sending failed: {str(e)}',
            }

order_email_service = OrderEmailService()