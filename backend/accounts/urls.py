from django.urls import path
from .views import register_user, login_user, get_user_balance, update_user_profile, get_signal_strength, get_signal_plans, purchase_signal_plan, admin_manage_signal_strength, admin_update_user_signal

urlpatterns = [
    path('register/', register_user, name='register'),
    path('login/', login_user, name='login'),
    path('balance/', get_user_balance, name='get_user_balance'),
    path('update-profile/', update_user_profile, name='update_user_profile'),
    path('signal/strength/', get_signal_strength, name='get_signal_strength'),
    path('signal/plans/', get_signal_plans, name='get_signal_plans'),
    path('signal/purchase/', purchase_signal_plan, name='purchase_signal_plan'),
    path('admin/signal-strength/', admin_manage_signal_strength, name='admin_manage_signal_strength'),
    path('admin/update-signal/<int:user_id>/', admin_update_user_signal, name='admin_update_user_signal'),
]
