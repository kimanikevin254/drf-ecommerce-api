from rest_framework import permissions

class IsCustomerOrAdminReadOnly(permissions.BasePermission):
    """
    Customers can create/view their own orders
    Admins can view all orders and view status
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Customers can create and view their own orders
        if request.user.is_customer:
            return request.method in ['GET', 'POST']
        
        # Admins can view all orders and update status
        if request.user.is_admin_user:
            return request.method in ['GET', 'PUT', 'PATCH']
            
        return False
    
    def has_object_permission(self, request, view, obj):
        # Customers can only access their own orders
        if request.user.is_customer:
            return obj.customer == request.user
        
        # Admins can access any order
        if request.user.is_admin_user:
            return True
            
        return False