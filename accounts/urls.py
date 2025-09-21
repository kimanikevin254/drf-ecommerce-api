from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('google/login/', view=views.google_login, name='google-login'),
    path('google/callback/', view=views.google_auth_callback, name='google-callback'),
]