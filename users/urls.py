from django.urls import path
from .views import RegisterView, LoginView, LogoutView, ProfileView, PasswordResetConfirmView, PasswordResetRequestView, AssignClientView, ClientRespondAssignmentView, ClientLawyerView, LawyerClientsListView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("lawyers/assign-client/", AssignClientView.as_view(), name="lawyers-assign-client"),
    path("clients/assignment/respond/", ClientRespondAssignmentView.as_view(), name="clients-assignment-respond"),
    path("lawyers/clients/", LawyerClientsListView.as_view(), name="lawyers-clients-list"),
    path("clients/lawyer/", ClientLawyerView.as_view(), name="clients-lawyer"),

]
