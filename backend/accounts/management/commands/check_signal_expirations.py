from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from accounts.models import User

class Command(BaseCommand):
    help = 'Check for expired signal plans and notify users'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        
        # Find users whose signal plans expire soon (within 24 hours)
        expiring_soon = User.objects.filter(
            signal_expires_at__lt=now + timezone.timedelta(hours=24),
            signal_expires_at__gt=now,
            signal_strength__gt=1  # Only include non-default signal plans
        )
        
        # Find users whose signal plans have just expired
        just_expired = User.objects.filter(
            signal_expires_at__lt=now,
            signal_expires_at__gt=now - timezone.timedelta(hours=1),  # Expired in the last hour
            signal_strength__gt=1  # Only users with active plans
        )
        
        # Send notifications for plans expiring soon
        for user in expiring_soon:
            try:
                hours_left = int((user.signal_expires_at - now).total_seconds() / 3600)
                subject = f"Signal Plan Expiring Soon - {hours_left} hours left"
                html_message = render_to_string('accounts/signal_expiring_email.html', {
                    'user': user,
                    'hours_left': hours_left,
                    'site_url': settings.SITE_URL,
                })
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f"Expiration warning sent to {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send expiration warning to {user.email}: {str(e)}"))
        
        # Send notifications for expired plans and reset them
        for user in just_expired:
            try:
                subject = "Signal Plan Expired"
                html_message = render_to_string('accounts/signal_expired_email.html', {
                    'user': user,
                    'site_url': settings.SITE_URL,
                })
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                # Reset user's signal strength to level 1 (default)
                user.signal_strength = 1
                user.save()
                
                self.stdout.write(self.style.SUCCESS(f"Expiration notification sent to {user.email} and signal reset"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to process expiration for {user.email}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Processed {expiring_soon.count()} expiring and {just_expired.count()} expired plans")) 