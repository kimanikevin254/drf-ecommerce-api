from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Define user types, as we'll have customers and admins
    USER_TYPES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )

    email = models.EmailField(unique=True) # Make email required and unique, since we'll be using OIDC
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='customer')
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    USERNAME_FIELD = 'email' # Use email as the login field
    
    REQUIRED_FIELDS = ['first_name', 'last_name'] # Required fields when creating a superuser

    def __str__(self):
        return self.email
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin'