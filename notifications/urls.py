from django.urls import path
from .views import NotificationListView, ActivityLogListView


urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications'),
    path('logs/', ActivityLogListView.as_view(), name='activity-logs'),
]

# Next we register these notification urls in our main backend/urls.py