from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email"""
        if not email:
            raise ValueError('Email field cannot be empty')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        # Only set passwords if provided(for superusers)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password() # Mark as no password for social auth users

        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", 'admin') # Make users admin type

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    # Remove username field
    username = None

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

    objects = UserManager() # use the custom manager

    def __str__(self):
        return self.email
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin'