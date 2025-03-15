from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'wallet_address', 'referral_code', 'transaction_pin', 'balance', 'phone_number', 'address', 'occupation', 'annual_income']
