from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.shortcuts import redirect
from django.http import JsonResponse

@api_view(['GET'])
@permission_classes([AllowAny])
def google_login(request):
    """Redirect to Google OAuth"""
    return redirect('/api/v1/accounts/google/login')

@login_required
def google_auth_callback(request):
    """
    After Google login, generate custom JWT tokens and return them
    """
    user = request.user

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return JsonResponse(
        data={
            'tokens': {
                'refresh': refresh_token,
                'access': access_token
            },
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
            }
        },
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """Admin login with email and password"""
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            data='Email and password are required.',
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(email=email, password=password)

    if user is None or user.user_type != 'admin':
        return Response(
            data='Invalid credentials or not an admin user.',
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return Response(
        data={
            'tokens': {
                'refresh': refresh_token,
                'access': access_token
            },
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
            }
        },
        status=status.HTTP_200_OK
    )