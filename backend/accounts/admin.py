from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('id', 'username', 'email', 'full_name', 'balance', 'wallet_address', 'phone_number', 'occupation', 'is_staff', 'is_active')
    readonly_fields = ('referral_code',)  # Add this line to make it read-only
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'email', 'phone_number', 'address', 'wallet_network', 'wallet_address', 'occupation', 'annual_income')}),
        ('Referral & Transactions', {'fields': ('referral_code', 'transaction_pin', 'balance')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    search_fields = ('email', 'username', 'full_name')
    ordering = ('email',)

admin.site.register(User, CustomUserAdmin)
