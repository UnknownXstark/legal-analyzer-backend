from django.urls import path
from .views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    NotificationDeleteView,
    ActivityLogListView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications'),
    path('logs/', ActivityLogListView.as_view(), name='activity-logs'),

    path('<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
    path('mark-all/', NotificationMarkAllReadView.as_view(), name='notification-mark-all'),
    path('<int:pk>/delete/', NotificationDeleteView.as_view(), name='notification-delete'),
]


# Next we register these notification urls in our main backend/urls.py