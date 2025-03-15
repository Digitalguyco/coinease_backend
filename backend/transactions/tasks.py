from django_q.tasks import schedule
from django_q.models import Schedule

def setup_investment_processing():
    # Schedule the task to run every minute
    schedule('django.core.management.call_command',
             'process_investments',
             schedule_type=Schedule.MINUTES,
             minutes=1) 