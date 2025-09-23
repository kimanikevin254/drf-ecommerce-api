import os

from .settings import *

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

# Security settings
DEBUG = False
ALLOWED_HOSTS = ['*'] # For testing purposes