from rest_framework import serializers
from .models import Transaction, Deposit, Withdrawal, Investment, InvestmentPlan

class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ['wallet_address', 'wallet_network']

class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['withdrawal_address', 'withdrawal_network', 'withdrawal_method']

class TransactionSerializer(serializers.ModelSerializer):
    deposit_details = DepositSerializer(read_only=True)
    withdrawal_details = WithdrawalSerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'type', 'status', 'amount', 'currency', 'date', 'description', 'deposit_details', 'withdrawal_details']

class InvestmentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentPlan
        fields = ['id', 'tier', 'level', 'daily_roi', 'min_deposit', 'max_deposit', 'duration']

class InvestmentSerializer(serializers.ModelSerializer):
    plan = InvestmentPlanSerializer(read_only=True)
    progress = serializers.SerializerMethodField()
    daily_return = serializers.SerializerMethodField()
    
    class Meta:
        model = Investment
        fields = ['id', 'plan', 'amount', 'currency', 'status', 'start_date', 'end_date', 
                 'total_returns', 'progress', 'daily_return']
    
    def get_progress(self, obj):
        return obj.calculate_progress()
    
    def get_daily_return(self, obj):
        return str(obj.calculate_daily_return()) 