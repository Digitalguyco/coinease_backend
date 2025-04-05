from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'referral_code', 'transaction_pin', 'balance', 'phone_number', 'address', 'occupation', 'annual_income']
        read_only_fields = ['id', 'referral_code', 'balance']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'password', 'transaction_pin']
        
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],
            transaction_pin=validated_data.get('transaction_pin', '')
        )
        return user
