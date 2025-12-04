from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.

User = settings.AUTH_USER_MODEL

PLAN_CHOICES = [
    ('free', 'Free'),
    ('premium', 'Premium'),
    ('business', 'Business'),
]

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    active = models.BooleanField(default=False)

    # Monthly usage tracking for free plan enforcement
    analysis_count = models.IntegerField(default=0)
    billing_cycle_start = models.DateTimeField(default=timezone.now)

    current_period_end = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def reset_if_new_cycle(self):
        """
        If billing_cycle_start is more than 30 days ago, reset analysis_count and set billing_cycle_start to now.
        (Simple monthly reset — adjust for exact billing from Stripe if needed)
        """
        from django.utils import timezone
        if (timezone.now() - self.billing_cycle_start).days >= 30:
            self.analysis_count = 0
            self.billing_cycle_start = timezone.now()
            self.save()

    def remaining_analyses(self):
        if self.plan == 'free':
            limit = 3
            return max(limit - self.analysis_count, 0)
        return -1  # -1 => unlimited

    def __str__(self):
        return f"{self.user} → {self.plan} (active={self.active})"