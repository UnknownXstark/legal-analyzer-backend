from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, LogoutView, ProfileView, PasswordResetConfirmView, PasswordResetRequestView, ClientRespondAssignmentView, ClientLawyerView, LawyerClientsListView, GoogleLoginView, CreateAssignmentRequestView, LawyerAssignmentRequestsList, ClientPendingRequestsList, ClientRespondAssignmentView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),

    # Lawyer-client assignment
    path("lawyers/assign-client/", CreateAssignmentRequestView.as_view(), name="lawyers-assign-client"),
    path('lawyers/assignment-requests/', LawyerAssignmentRequestsList.as_view(), name='lawyers-assignment-requests'),
    path('clients/assignment-requests/', ClientPendingRequestsList.as_view(), name='clients-assignment-requests'),
    path("clients/assignment/respond/", ClientRespondAssignmentView.as_view(), name="clients-assignment-respond"),
    path("lawyers/clients/", LawyerClientsListView.as_view(), name="lawyers-clients-list"),
    path("clients/lawyer/", ClientLawyerView.as_view(), name="clients-lawyer"),

    # JWT Refresh Token Endpoint
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Google OAuth2 Login
    path("google/", GoogleLoginView.as_view(), name="google-login"),
]
