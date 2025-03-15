from django.db import models
from django.conf import settings
import uuid
import math
from django.utils import timezone
from decimal import Decimal

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('investment', 'Investment'),
        ('investment_return', 'Investment Return'),
        ('investment_completed', 'Investment Completed'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    currency = models.CharField(max_length=10)  # BTC, ETH, USDT, etc.
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.type.capitalize()} of {self.amount} {self.currency} - {self.status.capitalize()}"


class Deposit(models.Model):
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='deposit_details')
    wallet_address = models.CharField(max_length=255)
    wallet_network = models.CharField(max_length=20, blank=True, null=True)  # ETH, BTC, etc.
    admin_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_deposits'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Deposit {self.transaction.id}"


class Withdrawal(models.Model):
    WITHDRAWAL_METHODS = (
        ('crypto', 'Cryptocurrency'),
        ('bank', 'Bank Transfer'),
        ('paypal', 'PayPal'),
        ('other', 'Other'),
    )
    
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='withdrawal_details')
    withdrawal_address = models.CharField(max_length=255)
    withdrawal_network = models.CharField(max_length=20, blank=True, null=True)
    withdrawal_method = models.CharField(max_length=20, choices=WITHDRAWAL_METHODS, default='crypto')
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='processed_withdrawals'
    )
    
    def __str__(self):
        return f"Withdrawal {self.transaction.id}"


class InvestmentPlan(models.Model):
    TIER_CHOICES = (
        ('starter', 'Starter'),
        ('pro', 'Pro'),
    )
    
    LEVEL_CHOICES = (
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    )
    
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    daily_roi = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    min_deposit = models.DecimalField(max_digits=15, decimal_places=2)
    max_deposit = models.DecimalField(max_digits=15, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes for testing (will be days in production)")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('tier', 'level')
    
    def __str__(self):
        return f"{self.tier.capitalize()} {self.level.capitalize()} Plan"


class Investment(models.Model):
    STATUS_CHOICES = (
        ('ongoing', 'Ongoing'),
        ('halfway', 'Halfway'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='investments')
    plan = models.ForeignKey(InvestmentPlan, on_delete=models.PROTECT, related_name='investments')
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='investment_details')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=10, default='USDT')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    total_returns = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_payout_date = models.DateTimeField(null=True, blank=True)
    next_payout_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.plan} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        # If this is a new investment, set the end date and next_payout_date
        if not self.pk:
            now = timezone.now()
            # Calculate end_date based on plan duration (in minutes for testing)
            if not self.end_date:
                self.end_date = now + timezone.timedelta(minutes=self.plan.duration)
            # Set next payout date to tomorrow (1 minute for testing)
            if not self.next_payout_date:
                self.next_payout_date = now + timezone.timedelta(minutes=1)
        
        super().save(*args, **kwargs)
    
    def calculate_progress(self):
        """Calculate investment progress percentage"""
        if self.status == 'completed':
            return 100
        
        total_duration = (self.end_date - self.start_date).total_seconds()
        elapsed_duration = (timezone.now() - self.start_date).total_seconds()
        
        if elapsed_duration >= total_duration:
            return 100
        
        progress = (elapsed_duration / total_duration) * 100
        return min(round(progress, 2), 99.99)  # Cap at 99.99% until officially completed
    
    def calculate_daily_return(self):
        """Calculate the daily return amount based on investment and ROI"""
        daily_return = (self.amount * self.plan.daily_roi) / Decimal('100.0')
        return daily_return.quantize(Decimal('0.01'))
    
    def process_payout(self):
        """Process daily investment returns"""
        if self.status == 'completed':
            print(f"Investment {self.id} is completed")
            return False
        
        now = timezone.now()
        
        # Handle the case where next_payout_date is None
        if self.next_payout_date is None:
            # Set next_payout_date to now + 1 minute for testing
            self.next_payout_date = now + timezone.timedelta(minutes=1)
            self.save()
            return False
        
        # Skip if not yet time for payout
        if now < self.next_payout_date:
            print(f"Not yet time for payout for investment {self.id}")
            return False
        
        # Calculate daily return
        daily_return = self.calculate_daily_return()
        
        # Add return to user's balance and update investment records
        self.user.balance += daily_return
        self.user.save()
        
        self.total_returns += daily_return
        self.last_payout_date = now
        self.next_payout_date = now + timezone.timedelta(minutes=1)  # Every minute for testing
        
        # Create return transaction
        Transaction.objects.create(
            user=self.user,
            type='investment_return',
            status='successful',
            amount=daily_return,
            currency=self.currency,
            description=f"Daily return from {self.plan} investment"
        )
        
        # Check if halfway through investment period
        progress = self.calculate_progress()
        if progress >= 50 and self.status == 'ongoing':
            self.status = 'halfway'
        
        # Check if investment is complete
        if now >= self.end_date and self.status != 'completed':
            # Change status to completed
            self.status = 'completed'
            
            # Return principal to user's balance
            self.user.balance += self.amount
            self.user.save()
            
            # Create completion transaction record
            Transaction.objects.create(
                user=self.user,
                type='investment_completed',
                status='successful',
                amount=self.amount,
                currency=self.currency,
                description=f"Investment principal returned from {self.plan} investment"
            )
        
        self.save()
        return True