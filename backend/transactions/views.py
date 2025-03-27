from django.shortcuts import render, redirect, get_object_or_404
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
import os
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponseRedirect

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
        'site_url': settings.SITE_URL,
        'token': settings.ADMIN_APPROVAL_TOKEN,
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

@api_view(['GET'])
def approve_deposit(request, transaction_id):
    """
    Approve a deposit transaction, update user balance, and mark it as successful.
    This function is meant to be called from an admin email link.
    """
    # Check for a valid token in the request
    token = request.GET.get('token')
    if not token or token != settings.ADMIN_APPROVAL_TOKEN:
        return Response(
            {'error': 'Unauthorized access'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Get the transaction and related deposit
        transaction = Transaction.objects.get(id=transaction_id, type='deposit', status='pending')
        deposit = Deposit.objects.get(transaction=transaction)
        
        # Execute update within a transaction to ensure atomicity
        with db_transaction.atomic():
            # Update user balance
            user = transaction.user
            user.balance += Decimal(transaction.amount)
            user.save()
            
            # Update transaction status
            transaction.status = 'successful'
            transaction.save()
            
        # Send confirmation email to user
        subject = "Deposit Approved"
        html_message = render_to_string('transactions/deposit_approved_email.html', {
            'user': user,
            'transaction': transaction,
            'deposit': deposit,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Failed to send email notification: {str(e)}")
        
        return Response({
            'status': 'success', 
            'message': f'Deposit of {transaction.amount} {transaction.currency} has been approved'
        })
        
    except Transaction.DoesNotExist:
        return Response(
            {'error': 'Transaction not found or already processed'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Deposit.DoesNotExist:
        return Response(
            {'error': 'Deposit details not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Error processing approval: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_deposits(request):
    """
    Get all pending deposits for admin review.
    This endpoint should be restricted to admin users only.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get all pending deposit transactions
    pending_transactions = Transaction.objects.filter(
        type='deposit',
        status='pending'
    ).select_related('user')
    
    # Get the related deposit objects
    pending_deposits = Deposit.objects.filter(
        transaction__in=pending_transactions
    ).select_related('transaction', 'transaction__user')
    
    # Create a custom response with transaction and deposit details
    result = []
    for deposit in pending_deposits:
        transaction = deposit.transaction
        result.append({
            'transaction_id': transaction.id,
            'user': {
                'id': transaction.user.id,
                'email': transaction.user.email,
                'full_name': transaction.user.full_name
            },
            'amount': transaction.amount,
            'currency': transaction.currency,
            'date': transaction.date,
            'wallet_address': deposit.wallet_address,
            'wallet_network': deposit.wallet_network
        })
    
    return Response(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_deposit_status(request, transaction_id):
    """
    Update the status of a deposit transaction to either 'successful' or 'failed'.
    This endpoint should be restricted to admin users only.
    """
    # Check if user is admin
    if not request.user.is_staff:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validate request data
    if 'status' not in request.data:
        return Response(
            {'error': 'Status field is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    new_status = request.data['status']
    if new_status not in ['successful', 'failed']:
        return Response(
            {'error': 'Status must be either "successful" or "failed"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get the transaction and related deposit
        transaction = Transaction.objects.get(id=transaction_id, type='deposit')
        deposit = Deposit.objects.get(transaction=transaction)
        
        # If transaction is already in the requested state, just return success
        if transaction.status == new_status:
            return Response({
                'status': 'success',
                'message': f'Deposit already marked as {new_status}'
            })
        
        # Execute update within a transaction to ensure atomicity
        with db_transaction.atomic():
            # If status is successful, update user balance
            if new_status == 'successful':
                user = transaction.user
                user.balance += Decimal(transaction.amount)
                user.save()
                
            # Update transaction status
            transaction.status = new_status
            transaction.save()
            
        # Send email to user
        subject = f"Deposit {new_status.capitalize()}"
        template = 'transactions/deposit_approved_email.html' if new_status == 'successful' else 'transactions/deposit_failed_email.html'
        
        # If we need a failed email template, we'd need to create it
        if new_status == 'failed' and not os.path.exists(os.path.join(settings.BASE_DIR, 'templates', 'transactions', 'deposit_failed_email.html')):
            template = 'transactions/deposit_approved_email.html'  # Fallback
        
        html_message = render_to_string(template, {
            'user': transaction.user,
            'transaction': transaction,
            'deposit': deposit,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [transaction.user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Failed to send email notification: {str(e)}")
        
        return Response({
            'status': 'success',
            'message': f'Deposit marked as {new_status}'
        })
        
    except Transaction.DoesNotExist:
        return Response(
            {'error': 'Transaction not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Deposit.DoesNotExist:
        return Response(
            {'error': 'Deposit details not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Error updating deposit status: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@staff_member_required
def admin_pending_deposits(request):
    """
    Django view that lists all pending deposits for admin approval.
    Only accessible to staff users and redirects to admin login if not logged in.
    """
    # Get all pending deposit transactions
    pending_transactions = Transaction.objects.filter(
        type='deposit',
        status='pending'
    ).select_related('user')
    
    # Get the related deposit objects
    pending_deposits = Deposit.objects.filter(
        transaction__in=pending_transactions
    ).select_related('transaction', 'transaction__user')
    
    # Prepare for template
    deposits = []
    for deposit in pending_deposits:
        transaction = deposit.transaction
        deposits.append({
            'id': transaction.id,
            'user': transaction.user,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'date': transaction.date,
            'wallet_address': deposit.wallet_address,
            'wallet_network': deposit.wallet_network or 'Not specified'
        })
    
    context = {
        'deposits': deposits,
        'title': 'Pending Deposits'
    }
    
    return render(request, 'admin/transactions/pending_deposits.html', context)

@staff_member_required
def admin_update_deposit_status(request, transaction_id):
    """
    Django view to update a deposit's status.
    Only accessible to staff users and redirects to admin login if not logged in.
    """
    transaction = get_object_or_404(Transaction, id=transaction_id, type='deposit')
    deposit = get_object_or_404(Deposit, transaction=transaction)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status not in ['successful', 'failed']:
            messages.error(request, 'Invalid status selected')
            return redirect('admin_pending_deposits')
        
        # If transaction is already in the requested state, just return
        if transaction.status == new_status:
            messages.info(request, f'Deposit was already marked as {new_status}')
            return redirect('admin_pending_deposits')
        
        # Execute update within a transaction to ensure atomicity
        with db_transaction.atomic():
            # If status is successful, update user balance
            if new_status == 'successful':
                user = transaction.user
                user.balance += Decimal(transaction.amount)
                user.save()
                
            # Update transaction status
            transaction.status = new_status
            transaction.save()
            
        # Send email to user
        subject = f"Deposit {new_status.capitalize()}"
        template = 'transactions/deposit_approved_email.html' if new_status == 'successful' else 'transactions/deposit_failed_email.html'
        
        # If we need a failed email template, we'd need to create it
        if new_status == 'failed' and not os.path.exists(os.path.join(settings.BASE_DIR, 'templates', 'transactions', 'deposit_failed_email.html')):
            template = 'transactions/deposit_approved_email.html'  # Fallback
        
        html_message = render_to_string(template, {
            'user': transaction.user,
            'transaction': transaction,
            'deposit': deposit,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [transaction.user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Failed to send email notification: {str(e)}")
            messages.warning(request, f"Action completed but email delivery failed: {str(e)}")
        
        messages.success(request, f'Deposit marked as {new_status} successfully')
        return redirect('admin_pending_deposits')
    
    # If GET request, show the form
    context = {
        'deposit': deposit,
        'transaction': transaction,
        'title': 'Update Deposit Status'
    }
    
    return render(request, 'admin/transactions/update_deposit.html', context)
