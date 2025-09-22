import logging
from africastalking.SMS import SMSService
from django.conf import settings

logger = logging.getLogger(__name__)

class OrderSMSSerive:
    """
    Service class for handling SMS notifications related to orders
    """
    def __init__(self):
        self.sms_client = SMSService(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY
        )

    def format_phone_number(self, phone):
        """
        Format phone number to the correct international format for Kenya
        """
        if phone.startswith('254'):
            return f'+{phone}'
        elif phone.startswith('0'):
            return f'+254{phone[1:]}'
        elif phone.startswith('7') or phone.startswith('1'):
            return f'+254{phone}'
        else:
            # Assume it's already in correct format
            return phone
        
    def create_order_confirmation_message(self, order):
        """
        Create the SMS message for order confirmation
        """
        return (
            f"Hi {order.customer.first_name}! "
            f"Your order #{order.id} for ${order.total_amount} has been confirmed. "
            f"We'll notify you when it's ready for delivery. Thank you!"
        )
    
    def send_order_confirmation_sms(self, order):
        """
        Send SMS to customer
        """
        try:
            if not order.customer_phone:
                logger.warning(f'No phone number for order {order.id}')
                return {'success': False, 'error': 'No phone number'}


            # Format phone number and message
            phone = self.format_phone_number(order.customer_phone)
            message = self.create_order_confirmation_message(order)

            # send SMS
            response = self.sms_client.send(message, [phone])

            return self._process_sms_response(response, phone, message)

        except Exception as e:
            logger.error(f"Failed to send SMS for order {order.id}: {str(e)}")
            return {
                'success': False,
                'error': f'SMS sending failed: {str(e)}',
                'phone': getattr(order, 'customer_phone', 'Unknown')
            }
        
    def _process_sms_response(self, response, phone, message):
        """Process SMS API response"""
        try:
            #  Check if response has expected structure
            sms_data = response.get('SMSMessageData', {})
            recipients = sms_data.get('Recipients', [])
            
            if not recipients:
                logger.error(f"No recipients in SMS response: {response}")
                return {
                    'success': False,
                    'error': 'No recipients found in API response',
                    'phone': phone
                }
            
            recipient = recipients[0]
            status = recipient.get('status', '')
            
            if status == 'Success':
                logger.info(f"SMS sent successfully to {phone}")
                return {
                    'success': True,
                    'phone': phone,
                    'message': message,
                    'cost': recipient.get('cost', 'N/A'),
                    'message_id': recipient.get('messageId', 'N/A'),
                    'status': status
                }
            else:
                logger.error(f"SMS failed with status: {status} for {phone}")
                return {
                    'success': False,
                    'error': status,
                    'phone': phone,
                    'status_code': recipient.get('statusCode', 'N/A')
                }
                
        except (KeyError, IndexError) as e:
            logger.error(f"Error processing SMS response: {e}")
            return {
                'success': False,
                'error': f'Error processing API response: {str(e)}',
                'phone': phone
            }
        
order_sms_service = OrderSMSSerive()