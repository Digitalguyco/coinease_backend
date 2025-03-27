from django.urls import path
from . import views

urlpatterns = [
    path('deposits/create/', views.create_deposit, name='create_deposit'),
    path('withdrawals/create/', views.create_withdrawal, name='create_withdrawal'),
    path('transactions/', views.get_user_transactions, name='user_transactions'),
    path('transactions/<uuid:transaction_id>/', views.get_transaction_detail, name='transaction_detail'),
    path('investment-plans/', views.get_investment_plans, name='investment_plans'),
    path('investments/create/', views.create_investment, name='create_investment'),
    path('investments/', views.get_user_investments, name='user_investments'),
    path('investments/<int:investment_id>/', views.get_investment_detail, name='investment_detail'),
    path('deposits/approve/<uuid:transaction_id>/', views.approve_deposit, name='approve_deposit'),
    path('deposits/pending/', views.get_pending_deposits, name='pending_deposits'),
    path('deposits/update-status/<uuid:transaction_id>/', views.update_deposit_status, name='update_deposit_status'),
    
    path('admin/pending-deposits/', views.admin_pending_deposits, name='admin_pending_deposits'),
    path('admin/update-deposit/<uuid:transaction_id>/', views.admin_update_deposit_status, name='admin_update_deposit'),
] 