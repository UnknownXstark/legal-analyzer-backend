from django.shortcuts import render
from django.db import models
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification, ActivityLog
from .serializers import NotificationSerializer, ActivityLogSerializer

# Create your views here.
class NotificationListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        
        notification.is_read = True
        notification.save()

        return Response({"message": "Notification marked as read."}, status=status.HTTP_200_OK)
    

class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"message": "All notifications marked as read."}, status=status.HTTP_200_OK)
    

class NotificationDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        
        notification.delete()
        return Response({"message": "Notification deleted."}, status=status.HTTP_200_OK)
    


class ActivityLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        user = self.request.user
        qs = ActivityLog.objects.all() if user.role == "admin" else ActivityLog.objects.filter(user=user)

        # Read ?type= from query params
        filter_type = self.request.query_params.get("type", None)

        if filter_type and filter_type != "all":
            filter_type = filter_type.lower()

            if filter_type == "upload":
                qs = qs.filter(action__icontains="upload")
            elif filter_type == "analysis":
                qs = qs.filter(action__icontains="analy")
            elif filter_type == "report":
                qs = qs.filter(action__icontains="report")
            elif filter_type == "download":
                qs = qs.filter(action__icontains="download")
            elif filter_type == "auth":
                qs = qs.filter(
                    models.Q(action__icontains="login")
                    | models.Q(action__icontains="logout")
                )

        return qs.order_by("-timestamp")