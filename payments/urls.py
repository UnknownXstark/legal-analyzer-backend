# payments/urls.py
from django.urls import path
from .views import CreateCheckoutSessionView, CreateBillingPortalView, SubscriptionStatusView, stripe_webhook

urlpatterns = [
    path("create-checkout-session/", CreateCheckoutSessionView.as_view(), name="create-checkout-session"),
    path("manage-billing-portal/", CreateBillingPortalView.as_view(), name="manage-billing-portal"),
    path("subscription-status/", SubscriptionStatusView.as_view(), name="subscription-status"),
    path("webhook/", stripe_webhook, name="stripe-webhook"),
]
