"""
Stripe billing integration.

Test mode:  set STRIPE_API_KEY=sk_test_... in .env
Live mode:  set STRIPE_API_KEY=sk_live_... in .env (switch when ready for production)

Create products and prices in the Stripe dashboard, then copy the price IDs
into STRIPE_PRICE_ID_STARTER / _PROFESSIONAL / _ENTERPRISE in .env.

Webhook:
  1. Run `stripe listen --forward-to localhost:8000/api/billing/webhook` during local dev
  2. Copy the printed signing secret into STRIPE_WEBHOOK_SECRET in .env
  3. In production, set the endpoint URL in your Stripe dashboard and use that secret
"""
import json
from typing import Optional

from cqc_lem.utilities.env_constants import (
    STRIPE_API_KEY,
    STRIPE_PRICE_ID_ENTERPRISE,
    STRIPE_PRICE_ID_PROFESSIONAL,
    STRIPE_PRICE_ID_STARTER,
    STRIPE_WEBHOOK_SECRET,
)
from cqc_lem.utilities.logger import myprint

# Map tier names → Stripe price IDs (populated from env at import time)
TIER_PRICE_MAP: dict[str, Optional[str]] = {
    "starter": STRIPE_PRICE_ID_STARTER,
    "professional": STRIPE_PRICE_ID_PROFESSIONAL,
    "enterprise": STRIPE_PRICE_ID_ENTERPRISE,
}


def _get_stripe():
    """Return the stripe module with the API key configured.
    Lazy import so the module loads even when STRIPE_API_KEY is unset (e.g. tests).
    """
    import stripe as _stripe
    _stripe.api_key = STRIPE_API_KEY
    return _stripe


def create_stripe_customer(email: str, user_id: int) -> Optional[str]:
    """Create a Stripe customer for a new user. Returns the customer ID or None on failure."""
    if not STRIPE_API_KEY:
        myprint("STRIPE_API_KEY not set — skipping Stripe customer creation")
        return None
    stripe = _get_stripe()
    try:
        customer = stripe.Customer.create(
            email=email,
            metadata={"user_id": str(user_id)},
        )
        myprint(f"Stripe customer created: {customer.id} for user_id={user_id}")
        return customer.id
    except Exception as e:
        myprint(f"Stripe customer creation failed for user_id={user_id}: {e}")
        return None


def create_checkout_session(
    stripe_customer_id: str,
    tier: str,
    success_url: str,
    cancel_url: str,
) -> Optional[str]:
    """Create a Stripe Checkout session for a subscription upgrade.
    Returns the checkout session URL, or None on failure.
    """
    price_id = TIER_PRICE_MAP.get(tier)
    if not price_id:
        myprint(f"No Stripe price ID configured for tier '{tier}'")
        return None
    if not STRIPE_API_KEY:
        myprint("STRIPE_API_KEY not set — cannot create checkout session")
        return None

    stripe = _get_stripe()
    try:
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url
    except Exception as e:
        myprint(f"Stripe checkout session creation failed for customer={stripe_customer_id}: {e}")
        return None


def create_portal_session(stripe_customer_id: str, return_url: str) -> Optional[str]:
    """Create a Stripe Billing Portal session so users can manage their subscription.
    Returns the portal URL, or None on failure.
    """
    if not STRIPE_API_KEY:
        myprint("STRIPE_API_KEY not set — cannot create portal session")
        return None
    stripe = _get_stripe()
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception as e:
        myprint(f"Stripe portal session creation failed for customer={stripe_customer_id}: {e}")
        return None


def validate_webhook(payload: bytes, sig_header: str) -> Optional[dict]:
    """Validate a Stripe webhook event using the signing secret.
    Returns the event as a plain Python dict on success, None on failure.

    The Stripe SDK v5+ returns a StripeObject (not a dict), which doesn't
    support .get(). We validate the signature via the SDK, then parse the
    raw payload as a dict so callers can use normal dict access.
    """
    if not STRIPE_WEBHOOK_SECRET:
        myprint("STRIPE_WEBHOOK_SECRET not set — cannot validate webhook")
        return None
    # Import stripe before the try block so it's in scope for the except clause.
    # If the package is not installed, the ImportError propagates immediately rather
    # than masking it as a NameError inside the except handler.
    stripe = _get_stripe()
    SignatureVerificationError = stripe.error.SignatureVerificationError
    try:
        # Raises on invalid signature — this is the only thing we need the SDK for here
        stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        # Return the raw payload as a plain dict for consistent .get() access
        return json.loads(payload.decode("utf-8"))
    except SignatureVerificationError as e:
        myprint(f"Stripe webhook signature invalid: {e}")
        return None
    except Exception as e:
        myprint(f"Stripe webhook validation failed: {e}")
        return None


def get_subscription_tier_from_price(price_id: str) -> Optional[str]:
    """Reverse-map a Stripe price ID back to our tier name."""
    for tier, pid in TIER_PRICE_MAP.items():
        if pid and pid == price_id:
            return tier
    return None


# Stripe subscription status → our DB status
_STRIPE_STATUS_MAP: dict[str, str] = {
    "active": "active",
    "trialing": "trial",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "cancelled",
    "incomplete": "inactive",
    "incomplete_expired": "inactive",
    "paused": "inactive",
}


def stripe_status_to_db(stripe_status: str) -> str:
    """Convert a Stripe subscription status string to our DB enum value."""
    return _STRIPE_STATUS_MAP.get(stripe_status, "inactive")


def fetch_subscription(stripe_subscription_id: str) -> Optional[dict]:
    """Retrieve a Stripe subscription object. Returns None on failure."""
    if not STRIPE_API_KEY:
        return None
    stripe = _get_stripe()
    try:
        sub = stripe.Subscription.retrieve(stripe_subscription_id)
        return sub
    except Exception as e:
        myprint(f"Could not fetch Stripe subscription {stripe_subscription_id}: {e}")
        return None
