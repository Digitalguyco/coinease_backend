from django.core.management.base import BaseCommand
from django.utils import timezone
from transactions.models import Investment

class Command(BaseCommand):
    help = 'Process all active investments to calculate returns'

    def handle(self, *args, **options):
        # Get all ongoing investments
        active_investments = Investment.objects.filter(status__in=['ongoing', 'halfway'])
        print(f"Found {active_investments.count()} active investments")
        
        processed_count = 0
        for investment in active_investments:
            print(f"Processing investment {investment.id}")
            if investment.process_payout():
                processed_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully processed {processed_count} investments')) 