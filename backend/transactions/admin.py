from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from .models import Transaction, Deposit, Withdrawal, InvestmentPlan, Investment

class DepositInline(admin.StackedInline):
    model = Deposit
    extra = 0
    readonly_fields = ('wallet_address', 'wallet_network')

class WithdrawalInline(admin.StackedInline):
    model = Withdrawal
    extra = 0
    readonly_fields = ('withdrawal_address', 'withdrawal_network', 'withdrawal_method')

class InvestmentInline(admin.StackedInline):
    model = Investment
    extra = 0
    readonly_fields = ('transaction', 'start_date', 'end_date', 'total_returns', 'last_payout_date', 'next_payout_date')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id',  'type', 'amount', 'currency', 'status', 'date')
    list_filter = ('type', 'status', 'currency', 'date')
    search_fields = ('user__email', 'user__full_name', 'description')
    readonly_fields = ('id', 'type', 'amount', 'currency', 'date')
    inlines = [DepositInline, WithdrawalInline, InvestmentInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    def pending_deposits_link(self, request):
        url = reverse('admin_pending_deposits')
        return format_html('<a href="{}">View Pending Deposits</a>', url)
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['pending_deposits_link'] = self.pending_deposits_link(request)
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('transaction_id',  'amount', 'currency', 'status', 'wallet_address', 'date')
    list_filter = ('transaction__status', 'transaction__date')
    search_fields = ('transaction__user__email', 'transaction__user__full_name', 'wallet_address')
    readonly_fields = ('transaction',)
    
    def transaction_id(self, obj):
        return obj.transaction.id
    
    def user(self, obj):
        return obj.transaction.user
    
    def amount(self, obj):
        return obj.transaction.amount
    
    def currency(self, obj):
        return obj.transaction.currency
    
    def status(self, obj):
        return obj.transaction.status
    
    def date(self, obj):
        return obj.transaction.date
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('transaction', 'transaction__user')
    
    # Actions for handling deposits
    actions = ['approve_deposits', 'reject_deposits']
    
    def approve_deposits(self, request, queryset):
        for deposit in queryset:
            transaction = deposit.transaction
            if transaction.status == 'pending':
                # Update transaction status
                transaction.status = 'successful'
                transaction.save()
                
                # Update user balance
                user = transaction.user
                user.balance += transaction.amount
                user.save()
                
                # Update deposit review info
                deposit.reviewed_by = request.user
                deposit.reviewed_at = timezone.now()
                deposit.save()
        
        self.message_user(request, f"Successfully approved {queryset.count()} deposits")
    approve_deposits.short_description = "Approve selected deposits and update balances"
    
    def reject_deposits(self, request, queryset):
        for deposit in queryset:
            transaction = deposit.transaction
            if transaction.status == 'pending':
                # Update transaction status
                transaction.status = 'failed'
                transaction.save()
                
                # Update deposit review info
                deposit.reviewed_by = request.user
                deposit.reviewed_at = timezone.now()
                deposit.save()
        
        self.message_user(request, f"Successfully rejected {queryset.count()} deposits")
    reject_deposits.short_description = "Reject selected deposits"

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'amount', 'currency', 'withdrawal_address', 'withdrawal_method', 'date')
    list_filter = ('withdrawal_method', 'transaction__date')
    search_fields = ('transaction__user__email', 'transaction__user__full_name', 'withdrawal_address')
    readonly_fields = ('transaction',)
    
    def transaction_id(self, obj):
        return obj.transaction.id
    
    def user(self, obj):
        return obj.transaction.user
    
    def amount(self, obj):
        return obj.transaction.amount
    
    def currency(self, obj):
        return obj.transaction.currency
    
    def date(self, obj):
        return obj.transaction.date
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('transaction', 'transaction__user')

@admin.register(InvestmentPlan)
class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = ('tier', 'level', 'daily_roi', 'min_deposit', 'max_deposit', 'duration', 'is_active')
    list_filter = ('tier', 'level', 'is_active')
    search_fields = ('tier', 'level')

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ( 'plan', 'amount', 'currency', 'status', 'start_date', 'end_date', 'total_returns', 'progress')
    list_filter = ('status', 'plan__tier', 'plan__level', 'currency')
    search_fields = ('user__email', 'user__full_name')
    readonly_fields = ('transaction', 'start_date', 'progress')
    
    def progress(self, obj):
        return f"{obj.calculate_progress():.2f}%"
