from django.urls import path
from .views import register_user, login_user, get_user_balance, update_user_profile

urlpatterns = [
    path('register/', register_user, name='register'),
    path('login/', login_user, name='login'),
    path('balance/', get_user_balance, name='get_user_balance'),
    path('update-profile/', update_user_profile, name='update_user_profile'),
]
