from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated



@api_view(['POST'])
def register_user(request):
    data = request.data
    if User.objects.filter(email=data['email']).exists():
        return Response({'error': 'Email already in use'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(
        username=data['email'],
        full_name=data['full_name'],
        email=data['email'],
        wallet_network=data.get('wallet_network', ''),
        wallet_address=data.get('wallet_address', ''),
        transaction_pin=data.get('transaction_pin', ''),
        password=data['password'],
    )
    send_mail(
        'Welcome to CoinEase',
        f'Welcome {data["full_name"]} to CoinEase.\n\nYour account has been created successfully.\n\nYour username is {data["email"]} and your password is {data["password"]}. Your Transaction Pin is {data["transaction_pin"]}.\n\nPlease login to your account to continue.',
        settings.EMAIL_HOST_USER,
        [data['email']],
        fail_silently=False
    )
    return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def login_user(request):
    data = request.data
    user = User.objects.filter(email=data['email']).first()
    if user and user.check_password(data['password']):
        refresh = RefreshToken.for_user(user)
        
        # Add comprehensive user data to the response
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'balance': str(user.balance),
            'wallet_network': user.wallet_network,  # Include the wallet network
            'wallet_address': user.wallet_address,
            'phone_number': user.phone_number if hasattr(user, 'phone_number') else None,
            'referral_code': user.referral_code,
            'address': user.address if hasattr(user, 'address') else None,
            'occupation': user.occupation if hasattr(user, 'occupation') else None,
            'annual_income': str(user.annual_income) if hasattr(user, 'annual_income') else None,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        }
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': user_data
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_balance(request):
    user = request.user
    return Response({
        'balance': str(user.balance),
        'user_id': user.id
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    user = request.user
    data = request.data
    
    # Fields that users are allowed to update
    allowed_fields = [
        'full_name', 'phone_number', 'address', 'occupation', 
        'annual_income', 'wallet_network', 'wallet_address'
    ]
    
    # Update fields if provided in the request
    for field in allowed_fields:
        if field in data:
            setattr(user, field, data[field])
    
    # Handle transaction PIN separately with additional validation
    if 'transaction_pin' in data:
        # Ensure the transaction PIN is exactly 4 characters
        pin = data['transaction_pin']
        if pin and len(pin) == 4:
            user.transaction_pin = pin
        else:
            return Response(
                {'error': 'Transaction PIN must be 4 digits'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Handle password change if provided
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    
    # Save user changes
    user.save()
    
    # Prepare response data
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'balance': str(user.balance),
        'wallet_network': user.wallet_network,
        'wallet_address': user.wallet_address,
        'phone_number': user.phone_number,
        'address': user.address,
        'occupation': user.occupation,
        'annual_income': str(user.annual_income) if user.annual_income else None,
    }
    
    return Response({
        'message': 'Profile updated successfully',
        'user': user_data
    }, status=status.HTTP_200_OK)
