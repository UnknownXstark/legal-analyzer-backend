# payments/serializers.py
from rest_framework import serializers
from .models import Subscription

class SubscriptionSerializer(serializers.ModelSerializer):
    analyses_remaining = serializers.SerializerMethodField()
    analyses_limit = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ["plan", "active", "analysis_count", "billing_cycle_start", "current_period_end", "cancel_at_period_end", "analyses_remaining", "analyses_limit"]

    def get_analyses_remaining(self, obj):
        return obj.remaining_analyses()

    def get_analyses_limit(self, obj):
        if obj.plan == 'free':
            return 3
        return -1  # unlimited
