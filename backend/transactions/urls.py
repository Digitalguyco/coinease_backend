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
] 