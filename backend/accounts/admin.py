from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SignalPlan, SignalPurchaseHistory

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('id', 'username', 'email', 'full_name', 'balance', 'wallet_address', 'phone_number', 'occupation', 'is_staff', 'is_active', 'signal_strength')
    readonly_fields = ('referral_code',)  # Add this line to make it read-only
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'email', 'phone_number', 'address', 'wallet_network', 'wallet_address', 'occupation', 'annual_income')}),
        ('Signal Information', {'fields': ('signal_strength', 'signal_expires_at')}),
        ('Referral & Transactions', {'fields': ('referral_code', 'transaction_pin', 'balance')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    search_fields = ('email', 'username', 'full_name')
    ordering = ('email',)

# First register the default User admin
admin.site.register(User, CustomUserAdmin)

@admin.register(SignalPlan)
class SignalPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'strength_level', 'price', 'is_active')
    list_filter = ('strength_level', 'is_active')
    search_fields = ('name', 'description')

@admin.register(SignalPurchaseHistory)
class SignalPurchaseHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'amount', 'date')
    list_filter = ('plan', 'date')
    search_fields = ('user__email', 'user__full_name')
    raw_id_fields = ('user', 'plan', 'transaction')
