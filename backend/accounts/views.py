from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, SignalPlan,  SignalPurchaseHistory
from transactions.models import Transaction
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.template.loader import render_to_string
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.html import strip_tags



@api_view(['POST'])
def register_user(request):
    data = request.data
    if User.objects.filter(email=data['email']).exists():
        return Response({'error': 'Email already in use'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(
        username=data['email'],
        full_name=data['full_name'],
        email=data['email'],
        transaction_pin=data.get('transaction_pin', ''),
        password=data['password'],
    )
    send_mail(
        'Welcome to CoinEase',
        f'Welcome {data["full_name"]} to CoinEase.\n\nYour account has been created successfully.\n\nYour username is {data["email"]} and your password is {data["password"]}. Your Transaction Pin is {data.get("transaction_pin", "")}.\n\nPlease login to your account to continue.',
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_signal_strength(request):
    """Get the current user's signal strength and status"""
    user = request.user
    
    # Check if signal has expired
    is_expired = user.signal_expires_at is None or user.signal_expires_at < timezone.now()
    
    # If expired, reset to level 1
    if is_expired and user.signal_strength > 1:
        user.signal_strength = 1
        user.save()
    
    # Create response with signal information
    response = {
        'signal_strength': user.signal_strength,
        'is_active': not is_expired,
        'expires_at': user.signal_expires_at,
        'days_remaining': (user.signal_expires_at - timezone.now()).days if user.signal_expires_at and not is_expired else 0,
        'can_process_trades': user.signal_strength >= 3 and not is_expired
    }
    
    return Response(response)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_signal_plans(request):
    """Get all available signal plans for purchase"""
    plans = SignalPlan.objects.filter(is_active=True)
    
    # Convert to list of dictionaries for the response
    plans_data = []
    for plan in plans:
        plans_data.append({
            'id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'price': plan.price,
            'strength_level': plan.strength_level,
            'duration_days': plan.duration_days
        })
    
    return Response(plans_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def purchase_signal_plan(request):
    """Purchase a signal plan to increase signal strength"""
    user = request.user
    data = request.data
    
    # Validate plan ID
    if 'plan_id' not in data:
        return Response(
            {'error': 'Plan ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        plan = SignalPlan.objects.get(id=data['plan_id'], is_active=True)
    except SignalPlan.DoesNotExist:
        return Response(
            {'error': 'Signal plan not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user has sufficient balance
    if user.balance < plan.price:
        return Response(
            {'error': 'Insufficient balance for this signal plan'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate expiration date
    expiration_date = timezone.now() + timezone.timedelta(days=plan.duration_days)
    
    # Process purchase within a transaction
    with transaction.atomic():
        # Deduct from user balance
        user.balance -= plan.price
        
        # Update signal strength and expiration date
        user.signal_strength = plan.strength_level
        user.signal_expires_at = expiration_date
        user.save()
        
        # Create transaction record
        tx = Transaction.objects.create(
            user=user,
            type='signal_purchase',
            status='successful',
            amount=plan.price,
            currency='USD',  # Assuming USD as default, modify as needed
            description=f"Purchase of {plan.name} signal plan for {plan.duration_days} days"
        )
        
        # Record signal purchase
        SignalPurchaseHistory.objects.create(
            user=user,
            plan=plan,
            amount=plan.price,
            transaction=tx
        )
    
    # Send confirmation email
    try:
        subject = "Signal Strength Upgraded"
        html_message = render_to_string('accounts/signal_upgraded_email.html', {
            'user': user,
            'plan': plan,
            'expiration_date': expiration_date,
            'site_url': settings.SITE_URL
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        # Log the error but don't fail the operation
        print(f"Failed to send signal upgrade email: {str(e)}")
    
    # Return updated signal information
    return Response({
        'status': 'success',
        'message': f'Successfully purchased {plan.name} signal plan',
        'signal_strength': user.signal_strength,
        'expires_at': expiration_date,
        'days_remaining': plan.duration_days,
        'transaction_id': tx.id
    })

@staff_member_required
def admin_manage_signal_strength(request):
    """Admin view to manage user signal strength"""
    # Get all users, ordered by expiration date and signal strength
    users = User.objects.all().order_by('signal_strength')
    
    # Include current time for template comparisons
    now = timezone.now()
    
    context = {
        'users': users,
        'now': now,
        'title': 'Manage Signal Strength'
    }
    
    return render(request, 'admin/accounts/manage_signal_strength.html', context)

@staff_member_required
def admin_update_user_signal(request, user_id):
    """Admin view to update a specific user's signal strength"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Update user's signal strength
        new_strength = int(request.POST.get('signal_strength', user.signal_strength))
        
        # Handle expiration date
        days_to_add = int(request.POST.get('duration_days', 0))
        
        if days_to_add > 0:
            # Set or extend expiration
            if user.signal_expires_at and user.signal_expires_at > timezone.now():
                # Extend existing plan
                user.signal_expires_at = user.signal_expires_at + timezone.timedelta(days=days_to_add)
            else:
                # Set new expiration
                user.signal_expires_at = timezone.now() + timezone.timedelta(days=days_to_add)
        
        user.signal_strength = new_strength
        user.save()
        
        messages.success(request, f"Signal strength for {user.email} updated successfully")
        return redirect('admin_manage_signal_strength')
    
    # Calculate days remaining
    days_remaining = 0
    if user.signal_expires_at and user.signal_expires_at > timezone.now():
        days_remaining = (user.signal_expires_at - timezone.now()).days
    
    context = {
        'user': user,
        'days_remaining': days_remaining,
        'is_expired': user.signal_expires_at is None or user.signal_expires_at < timezone.now(),
        'title': f'Update Signal for {user.email}'
    }
    
    return render(request, 'admin/accounts/update_user_signal.html', context)
