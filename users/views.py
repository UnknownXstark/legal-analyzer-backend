# users/views.py
from django.shortcuts import render
from django.db import transaction
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView  # <= needed
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import ClientAssignment, User, AssignmentRequest
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ClientAssignmentSerializer,
    AssignmentRequestSerializer,
    CreateAssignmentRequestSerializer,
)
from notifications.utils import create_notification, log_activity
from django.core.mail import send_mail
from .permissions import IsLawyer
from rest_framework.exceptions import NotFound
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Utilities for password reset
from django.contrib.auth.tokens import PasswordResetTokenGenerator  # <= needed
from django.utils.encoding import force_bytes, force_str              # <= needed
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode  # <= needed
import os

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        response_data = {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get("email") or request.data.get("username")
        password = request.data.get("password")

        if not identifier or not password:
            return Response({"detail": "Email/Username and password required"}, status=400)

        # Try login by email
        try:
            user_obj = User.objects.get(email=identifier)
            username = user_obj.username
        except User.DoesNotExist:
            # Try login by username
            username = identifier

        user = authenticate(request, username=username, password=password)

        if not user:
            return Response({"detail": "Invalid credentials"}, status=401)
        
        # Superusers are always admins
        if user.is_superuser:
            user.role = "admin"
            user.save()
        
        create_notification(user, "Login successful")
        log_activity(user, "User logged in", {"email": user.email})

        refresh = RefreshToken.for_user(user)

        return Response({
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=200)
    

class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        create_notification(user, "Logout successful")
        log_activity(user, "User logged out", None)
        
        return Response({"detail": "Logged out successfully"}, status=200)
    

class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal whether the email exists
            return Response({"message": "If user exists, a reset link has been sent."}, status=200)

        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Frontend route — adjust port if needed
        reset_link = f"http://localhost:5173/reset-password/{uid}/{token}"

        send_mail(
            subject="Reset Your Password",
            message=f"Click the link to reset your password: {reset_link}",
            from_email=None,  # uses DEFAULT_FROM_EMAIL from settings
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"message": "Password reset email sent."}, status=200)
    

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data["uidb64"]
        token = serializer.validated_data["token"]
        password = serializer.validated_data["password"]

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({"error": "Invalid link"}, status=400)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({"error": "Token invalid or expired"}, status=400)

        user.set_password(password)
        user.save()

        return Response({"message": "Password reset successful"}, status=200)


# class AssignClientView(generics.GenericAPIView):
#     serializer_class = CreateAssignmentSerializer
#     permission_classes = [IsAuthenticated, IsLawyer]

#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         client = User.objects.get(id=serializer.validated_data["client_id"])

#         assignment = ClientAssignment.objects.create(
#             lawyer=request.user,
#             client=client,
#             status="pending"
#         )

#         return Response(ClientAssignmentSerializer(assignment).data, status=201)


# class ClientRespondAssignmentView(generics.GenericAPIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         assignment_id = request.data.get("assignment_id")
#         action = request.data.get("action")

#         if action not in ["accept", "reject"]:
#             return Response({"error": "Invalid action"}, status=400)

#         try:
#             assignment = ClientAssignment.objects.get(id=assignment_id)
#         except ClientAssignment.DoesNotExist:
#             return Response({"error": "Assignment not found"}, status=404)

#         # Only the client can respond
#         if assignment.client != request.user:
#             return Response({"error": "Not allowed"}, status=403)

#         assignment.status = "accepted" if action == "accept" else "rejected"
#         assignment.save()

#         return Response({"message": f"Assignment {action}ed"})


class LawyerClientsListView(generics.ListAPIView):
    serializer_class = ClientAssignmentSerializer
    permission_classes = [IsAuthenticated, IsLawyer]

    def get_queryset(self):
        return ClientAssignment.objects.filter(
            lawyer=self.request.user,
            status="accepted"
        )


class ClientLawyerView(generics.RetrieveAPIView):
    serializer_class = ClientAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.lawyer_assignment
        except ClientAssignment.DoesNotExist:
            raise NotFound("Client has no assigned lawyer")


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        credential = request.data.get("credential")

        if not credential:
            return Response({"error": "Missing Google credential"}, status=400)

        try:
            # verify token
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
            )

            email = idinfo.get("email")
            username = email.split("@")[0]

            # check if user exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "role": "individual"  # default role
                }
            )

            # ensure username unique
            if created:
                if User.objects.filter(username=username).exists():
                    user.username = f"{username}_{user.id}"
                    user.save()

            refresh = RefreshToken.for_user(user)

            return Response({
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            })

        except Exception as e:
            print("Google Login Error:", e)
            return Response({"error": "Invalid Google token"}, status=400)
        
class CreateAssignmentRequestView(generics.GenericAPIView):
    """
    Lawyer -> create an assignment request to a client
    POST /api/users/lawyers/assign-client/
    payload: { client_id: int, message?: string }
    """
    serializer_class = CreateAssignmentRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsLawyer]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_id = serializer.validated_data["client_id"]
        message = serializer.validated_data.get("message", "")

        # Safety checks already done in serializer but re-check unique constraint
        client = User.objects.get(id=client_id)

        # Prevent duplicate requests at the DB level
        obj, created = AssignmentRequest.objects.get_or_create(
            lawyer=request.user,
            client=client,
            defaults={"message": message}
        )

        if not created:
            # If existing but rejected/withdrawn allow re-creating by updating status back to pending
            if obj.status in ("rejected", "withdrawn"):
                obj.status = "pending"
                obj.message = message or obj.message
                obj.save()
                created = True

        return Response(AssignmentRequestSerializer(obj).data, status=201 if created else 200)


class LawyerAssignmentRequestsList(generics.ListAPIView):
    """
    GET /api/users/lawyers/assignment-requests/
    List requests the current lawyer created
    """
    permission_classes = [permissions.IsAuthenticated, IsLawyer]
    serializer_class = AssignmentRequestSerializer

    def get_queryset(self):
        return AssignmentRequest.objects.filter(lawyer=self.request.user)


class ClientPendingRequestsList(generics.ListAPIView):
    """
    GET /api/users/clients/assignment-requests/
    List requests delivered to current client (pending only)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssignmentRequestSerializer

    def get_queryset(self):
        return AssignmentRequest.objects.filter(client=self.request.user, status="pending")


class ClientRespondAssignmentView(generics.GenericAPIView):
    """
    POST /api/users/clients/assignment/respond/
    payload: { assignment_id: int, action: 'accept' | 'reject' }
    On accept -> create ClientAssignment (atomic). If client already has an assignment, return error.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        assignment_id = request.data.get("assignment_id")
        action = request.data.get("action")

        if action not in ("accept", "reject"):
            return Response({"error": "Invalid action"}, status=400)

        try:
            req = AssignmentRequest.objects.get(id=assignment_id, client=request.user)
        except AssignmentRequest.DoesNotExist:
            return Response({"error": "Assignment request not found"}, status=404)

        if req.status != "pending":
            return Response({"error": "Request already responded to"}, status=400)

        if action == "reject":
            req.status = "rejected"
            req.save()
            return Response({"message": "Request rejected"}, status=200)

        # action == "accept"
        # Ensure client still has no accepted assignment (race-safe with transaction)
        with transaction.atomic():
            # Re-fetch inside transaction
            client = User.objects.select_for_update().get(id=request.user.id)
            if hasattr(client, "lawyer_assignment"):
                return Response({"error": "Client already has an assigned lawyer"}, status=400)

            # Create ClientAssignment
            assignment = ClientAssignment.objects.create(
                lawyer=req.lawyer,
                client=req.client,
                status="accepted"
            )

            # Mark request accepted
            req.status = "accepted"
            req.save()

        return Response({"message": "Assignment accepted", "assignment": {
            "id": assignment.id,
            "lawyer": str(assignment.lawyer),
            "client": str(assignment.client),
            "status": assignment.status
        }}, status=200)