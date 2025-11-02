from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Notification, ActivityLog
from .serializers import NotificationSerializer, ActivityLogSerializer

# Create your views here.
class NotificationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    

class ActivityLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return ActivityLog.objects.all().order_by('-timestamp')
        return ActivityLog.objects.filter(user=user).order_by('-timestamp')
