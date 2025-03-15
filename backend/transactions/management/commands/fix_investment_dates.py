from django.core.management.base import BaseCommand
from django.utils import timezone
from transactions.models import Investment

class Command(BaseCommand):
    help = 'Fix investments with NULL next_payout_date'

    def handle(self, *args, **options):
        # Find investments with NULL next_payout_date
        investments = Investment.objects.filter(next_payout_date__isnull=True)
        count = investments.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No investments need fixing'))
            return
            
        now = timezone.now()
        for investment in investments:
            investment.next_payout_date = now + timezone.timedelta(minutes=1)
            investment.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully fixed {count} investments')) 