from rest_framework.permissions import BasePermission

class IsLawyer(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'lawyer'
    

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'
    
# Role Based Permission Enforcement:
    # Just makes sure users cant access dashboards not meant for them.
    # Add them to views, in each respective dashboardview class.