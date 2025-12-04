from django.contrib import admin
from .models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "active", "analysis_count", "billing_cycle_start", "current_period_end")
    search_fields = ("user__username", "user__email", "stripe_customer_id", "stripe_subscription_id")