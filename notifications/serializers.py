from rest_framework import serializers
from .models import Notification, ActivityLog


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']


class ActivityLogSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = ['id', 'action', 'timestamp', 'details', 'type']

    def get_type(self, obj):
        """Derive activity type from 'action' text."""
        action = obj.action.lower()

        if "upload" in action:
            return "upload"
        if "analy" in action:
            return "analysis"
        if "report" in action:
            return "report"
        if "download" in action:
            return "download"
        if "login" in action or "logout" in action:
            return "auth"

        return "other"