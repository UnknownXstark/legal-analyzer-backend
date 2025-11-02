from .models import Notification, ActivityLog

def create_notification(user, message):
    Notification.objects.create(user=user, message=message)

def log_activity(user, action, details=None):
    ActivityLog.objects.create(user=user, action=action, details=details or {})



# These helper functions lets us easily call:
    # create_notification(request.user, "Your document has been analyzed successfully.")
    # log_activity(request.user, "Uploaded a document", {"document_id": 2})
# from anywhere in the project.
# Next we hook these into existing processing in our document/views.py
