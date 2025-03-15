from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Transaction, Deposit, Withdrawal, Investment, InvestmentPlan
from .serializers import TransactionSerializer, DepositSerializer, InvestmentSerializer, InvestmentPlanSerializer
from django.urls import reverse
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal

# Create your views here.

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_deposit(request):
    """Create a new deposit transaction"""
    user = request.user
    data = request.data
    
    # Validate required fields
    required_fields = ['amount', 'currency', 'wallet_address']
    for field in required_fields:
        if field not in data:
            return Response(
                {'error': f'Missing required field: {field}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Create transaction first
    transaction = Transaction.objects.create(
        user=user,
        type='deposit',
        status='pending',
        amount=data['amount'],
        currency=data['currency'],
        description=data.get('description', f"Deposit of {data['amount']} {data['currency']}")
    )
    
    # Create deposit record
    deposit = Deposit.objects.create(
        transaction=transaction,
        wallet_address=data['wallet_address'],
        wallet_network=data.get('wallet_network', '')
    )
    
    # Send email notification to admin
    admin_url = f"{settings.SITE_URL}{reverse('admin:accounts_user_change', args=[user.id])}"
    transaction_url = f"{settings.SITE_URL}{reverse('admin:transactions_transaction_change', args=[transaction.id])}"
    
    subject = f"Deposit Alert: {user.full_name} ({user.email})"
    html_message = render_to_string('transactions/deposit_email.html', {
        'user': user,
        'transaction': transaction,
        'deposit': deposit,
        'admin_url': admin_url,
        'transaction_url': transaction_url,
    })
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Failed to send email notification: {str(e)}")
    
    # Return the created transaction
    serializer = TransactionSerializer(transaction)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_transactions(request):
    """Get all transactions for the current user"""
    user = request.user
    transactions = Transaction.objects.filter(user=user)
    
    # Filter by type if provided
    transaction_type = request.query_params.get('type')
    if transaction_type:
        transactions = transactions.filter(type=transaction_type)
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transaction_detail(request, transaction_id):
    """Get details of a specific transaction"""
    try:
        transaction = Transaction.objects.get(id=transaction_id, user=request.user)
    except Transaction.DoesNotExist:
        return Response(
            {'error': 'Transaction not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = TransactionSerializer(transaction, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_withdrawal(request):
    """Process an immediate withdrawal for the user"""
    user = request.user
    data = request.data
    
    # Validate required fields
    required_fields = ['amount', 'currency', 'withdrawal_address', 'withdrawal_network', 'transaction_pin']
    for field in required_fields:
        if field not in data:
            return Response(
                {'error': f'Missing required field: {field}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Parse and validate amount
    try:
        amount = Decimal(data['amount'])
        if amount <= 0:
            return Response(
                {'error': 'Amount must be greater than zero'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError,):
        return Response(
            {'error': 'Invalid amount format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user has sufficient balance
    if user.balance < amount:
        return Response(
            {'error': 'Insufficient balance for this withdrawal'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Execute withdrawal within a transaction to ensure atomicity
    with db_transaction.atomic():
        # Deduct from user balance
        user.balance -= amount
        user.save()
        
        # Create transaction record
        transaction = Transaction.objects.create(
            user=user,
            type='withdrawal',
            status='successful',
            amount=amount,
            currency=data['currency'],
            description=data.get('description', f"Withdrawal of {amount} {data['currency']} to {data['withdrawal_address']}")
        )
        
        # Create withdrawal detail record (similar to Deposit)
        Withdrawal.objects.create(
            transaction=transaction,
            withdrawal_address=data['withdrawal_address'],
            withdrawal_network=data.get('withdrawal_network', ''),
            withdrawal_method=data.get('withdrawal_method', 'crypto')
        )
    
    # Return the created transaction
    serializer = TransactionSerializer(transaction)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_investment(request):
    """Create a new investment from user balance"""
    user = request.user
    data = request.data
    
    # Validate required fields
    required_fields = ['plan_id', 'amount', 'currency']
    for field in required_fields:
        if field not in data:
            return Response(
                {'error': f'Missing required field: {field}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Validate plan exists
    try:
        plan = InvestmentPlan.objects.get(id=data['plan_id'], is_active=True)
    except InvestmentPlan.DoesNotExist:
        return Response(
            {'error': 'Investment plan not found or inactive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Parse and validate amount
    try:
        amount = Decimal(data['amount'])
        if amount <= 0:
            return Response(
                {'error': 'Amount must be greater than zero'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except:
        return Response(
            {'error': 'Invalid amount format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate investment amount is within plan limits
    if amount < plan.min_deposit:
        return Response(
            {'error': f'Minimum deposit for this plan is {plan.min_deposit}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if amount > plan.max_deposit:
        return Response(
            {'error': f'Maximum deposit for this plan is {plan.max_deposit}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user has sufficient balance
    if user.balance < amount:
        return Response(
            {'error': 'Insufficient balance for this investment'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Execute investment within a transaction to ensure atomicity
    with db_transaction.atomic():
        # Deduct from user balance
        user.balance -= amount
        user.save()
        
        # Create transaction record
        transaction = Transaction.objects.create(
            user=user,
            type='investment',
            status='successful',
            amount=amount,
            currency=data['currency'],
            description=f"Investment in {plan.tier.capitalize()} {plan.level.capitalize()} Plan"
        )
        
        # Create investment record
        investment = Investment.objects.create(
            user=user,
            plan=plan,
            transaction=transaction,
            amount=amount,
            currency=data['currency'],
            status='ongoing',
            end_date=timezone.now() + timezone.timedelta(minutes=plan.duration)
        )
    
    # Return the created investment
    serializer = InvestmentSerializer(investment)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_investments(request):
    """Get all investments for the current user"""
    user = request.user
    investments = Investment.objects.filter(user=user)
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        investments = investments.filter(status=status_filter)
    
    serializer = InvestmentSerializer(investments, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_investment_detail(request, investment_id):
    """Get details of a specific investment"""
    try:
        investment = Investment.objects.get(id=investment_id, user=request.user)
    except Investment.DoesNotExist:
        return Response(
            {'error': 'Investment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Process payout to update status if needed
    investment.process_payout()
    
    serializer = InvestmentSerializer(investment)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_investment_plans(request):
    """Get all available investment plans"""
    plans = InvestmentPlan.objects.filter(is_active=True)
    serializer = InvestmentPlanSerializer(plans, many=True)
    return Response(serializer.data)
