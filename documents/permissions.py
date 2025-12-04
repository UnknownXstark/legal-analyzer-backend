from rest_framework.permissions import BasePermission
from users.models import ClientAssignment

class IsLawyer(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'lawyer'
    

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'
    
# Role Based Permission Enforcement:
    # Just makes sure users cant access dashboards not meant for them.
    # Add them to views, in each respective dashboardview class.

class IsDocumentParticipant(BasePermission):
    """
    Allow access if:
     - request.user is the document owner,
     - or request.user is an admin (role == 'admin' or is_superuser),
     - or request.user is the accepted lawyer assigned to this client.
    """

    def has_object_permission(self, request, view, obj):
        # obj is a Document instance
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Admins always allowed
        if getattr(user, "role", None) == "admin" or user.is_superuser:
            return True

        # Owner allowed
        if obj.user_id == user.id:
            return True

        # If the request user is a lawyer and is accepted for this client
        if getattr(user, "role", None) == "lawyer":
            # check accepted assignment exists
            return ClientAssignment.objects.filter(lawyer=user, client_id=obj.user_id, status="accepted").exists()

        return False