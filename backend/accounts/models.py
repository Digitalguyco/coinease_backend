import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
import json

def generate_referral_code():
    """Generate a unique 8-character referral code."""
    return str(uuid.uuid4().hex[:8]).upper()

class User(AbstractUser):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    wallet_network = models.CharField(max_length=10, blank=True, null=True)  # Store ETH, BTC, etc.
    wallet_address = models.CharField(max_length=255, blank=True, null=True)
    referral_code = models.CharField(max_length=10, unique=True, editable=False, default=generate_referral_code)
    transaction_pin = models.CharField(max_length=4, blank=True, null=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    occupation = models.CharField(max_length=255, blank=True, null=True)
    annual_income = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    id_number = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='referrals')
    
    # Signal strength related fields
    signal_strength = models.IntegerField(default=1, choices=[
        (1, 'Very Low'),
        (2, 'Low'),
        (3, 'Medium'),
        (4, 'High'),
    ], help_text="Current signal strength (1-4)")
    signal_expires_at = models.DateTimeField(null=True, blank=True, help_text="When the current signal plan expires")
    signal_last_updated = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Check if this is an update and if balance has changed
        if self.pk is not None:
            old_user = User.objects.get(pk=self.pk)
            balance_changed = old_user.balance != self.balance
        else:
            balance_changed = False
            
        # Save the user
        super().save(*args, **kwargs)
        
        # If balance changed, send update via WebSocket
        # if balance_changed:
        #     channel_layer = get_channel_layer()
        #     async_to_sync(channel_layer.group_send)(
        #         f'balance_{self.pk}',
        #         {
        #             'type': 'balance_message',
        #             'message': {
        #                 'balance': str(self.balance),
        #                 'user_id': self.pk
        #             }
        #         }
        #     )

# Signal Strength Plans
class SignalPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=18, decimal_places=8)
    strength_level = models.IntegerField(choices=[
        (1, 'Very Low'),
        (2, 'Low'),
        (3, 'Medium'),
        (4, 'High'),
    ])
    duration_days = models.IntegerField(help_text="Duration of the plan in days")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - Level {self.strength_level} ({self.duration_days} days)"

# Signal Purchase History
class SignalPurchaseHistory(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signal_purchases')
    # plan = models.ForeignKey(SignalPlan, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    # transaction = models.ForeignKey('transactions.Transaction', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name} on {self.date.strftime('%Y-%m-%d')}"
