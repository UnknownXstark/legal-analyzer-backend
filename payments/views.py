# payments/views.py
import os
import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Subscription
from .serializers import SubscriptionSerializer
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


# Utility: get or create Subscription model instance
def get_or_create_subscription(user):
    sub, created = Subscription.objects.get_or_create(user=user)
    return sub


# ============================================================
#   CREATE CHECKOUT SESSION
# ============================================================
class CreateCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan = request.data.get("plan")
        if plan not in ("premium", "business"):
            return Response({"error": "Invalid plan"}, status=400)

        price_env = "STRIPE_PRICE_ID_PREMIUM" if plan == "premium" else "STRIPE_PRICE_ID_BUSINESS"
        price_id = os.environ.get(price_env)
        if not price_id:
            return Response({"error": "Stripe price not configured"}, status=500)

        user = request.user

        # Ensure Stripe customer exists
        try:
            sub_obj = get_or_create_subscription(user)
            if sub_obj.stripe_customer_id:
                stripe_customer_id = sub_obj.stripe_customer_id
            else:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.username,
                    metadata={"user_id": user.id},
                )
                stripe_customer_id = customer["id"]
                sub_obj.stripe_customer_id = stripe_customer_id
                sub_obj.save()

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="subscription",
                customer=stripe_customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=os.environ.get("STRIPE_SUCCESS_URL"),
                cancel_url=os.environ.get("STRIPE_CANCEL_URL"),
                metadata={"user_id": str(user.id), "plan": plan},
            )

            # IMPORTANT: return ONLY checkout_url
            return Response({"checkout_url": checkout_session.url})

        except Exception as e:
            return Response({"error": str(e)}, status=500)


# ============================================================
#   BILLING PORTAL (MANAGE SUBSCRIPTION)
# ============================================================
class CreateBillingPortalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        sub_obj = get_or_create_subscription(request.user)
        if not sub_obj.stripe_customer_id:
            return Response({"error": "No stripe customer found"}, status=400)

        try:
            session = stripe.billing_portal.Session.create(
                customer=sub_obj.stripe_customer_id,
                return_url=os.environ.get("STRIPE_SUCCESS_URL"),
            )

            # IMPORTANT: return ONLY portal_url
            return Response({"portal_url": session.url})

        except Exception as e:
            return Response({"error": str(e)}, status=500)


# ============================================================
#   SUBSCRIPTION STATUS
# ============================================================
class SubscriptionStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sub_obj = get_or_create_subscription(request.user)
        sub_obj.reset_if_new_cycle()

        serializer = SubscriptionSerializer(sub_obj)

        return Response({
            "plan": sub_obj.plan,
            "status": "active" if sub_obj.active else "inactive",
            "current_period_end": sub_obj.current_period_end,
            "cancel_at_period_end": sub_obj.cancel_at_period_end,
            "usage": {
                "analyses_used": sub_obj.analysis_count,
                "analyses_limit": -1 if sub_obj.plan != "free" else 3,
            },
            **serializer.data
        })


# ============================================================
#   STRIPE WEBHOOK HANDLER
# ============================================================
@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    # Validate
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except Exception:
        return HttpResponse(status=400)

    # Handle event types
    try:
        # -------------------------
        # CHECKOUT COMPLETED
        # -------------------------
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            customer_id = session.get("customer")
            metadata = session.get("metadata", {})
            user_id = metadata.get("user_id")
            plan = metadata.get("plan")

            stripe_sub_id = session.get("subscription")

            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(id=user_id).first()

            if user:
                sub_obj, _ = Subscription.objects.get_or_create(user=user)
                sub_obj.stripe_customer_id = customer_id
                sub_obj.stripe_subscription_id = stripe_sub_id
                sub_obj.plan = plan
                sub_obj.active = True

                # Subscription period
                try:
                    stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
                    period_end = stripe_sub["current_period_end"]
                    sub_obj.current_period_end = timezone.datetime.fromtimestamp(
                        period_end, tz=timezone.utc
                    )
                except Exception:
                    pass

                sub_obj.save()

        # -------------------------
        # SUBSCRIPTION UPDATED
        # -------------------------
        elif event["type"] == "customer.subscription.updated":
            sub = event["data"]["object"]
            stripe_sub_id = sub.get("id")
            customer_id = sub.get("customer")
            status = sub.get("status")

            plan_items = sub.get("items", {}).get("data", [])
            plan_price_id = plan_items[0]["price"]["id"] if plan_items else None

            try:
                subscription_obj = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
            except Subscription.DoesNotExist:
                subscription_obj = Subscription.objects.filter(stripe_customer_id=customer_id).first()

            if subscription_obj:
                subscription_obj.active = status in ("active", "trialing")
                subscription_obj.current_period_end = timezone.datetime.fromtimestamp(
                    sub.get("current_period_end"), tz=timezone.utc
                )

                # Map Stripe price → plan label
                if plan_price_id == os.environ.get("STRIPE_PRICE_ID_PREMIUM"):
                    subscription_obj.plan = "premium"
                elif plan_price_id == os.environ.get("STRIPE_PRICE_ID_BUSINESS"):
                    subscription_obj.plan = "business"

                subscription_obj.cancel_at_period_end = sub.get("cancel_at_period_end", False)
                subscription_obj.save()

        # -------------------------
        # SUBSCRIPTION DELETED
        # -------------------------
        elif event["type"] == "customer.subscription.deleted":
            sub = event["data"]["object"]
            stripe_sub_id = sub.get("id")

            try:
                subscription_obj = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
                subscription_obj.active = False
                subscription_obj.plan = "free"
                subscription_obj.analysis_count = 0
                subscription_obj.stripe_subscription_id = None
                subscription_obj.save()
            except Subscription.DoesNotExist:
                pass

    except Exception:
        return HttpResponse(status=500)

    return HttpResponse(status=200)
