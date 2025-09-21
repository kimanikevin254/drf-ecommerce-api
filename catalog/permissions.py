from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """Custom permission to only write permissions to admins"""
    def has_permission(self, request, view):
        # Read permissions for anyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # write permissions for admins only
        return request.user.is_authenticated and request.user.is_admin_user