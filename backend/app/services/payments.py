





from __future__ import annotations

import logging
from typing import Any

import stripe

from ..config import get_settings
from ..db_models import Order

log = logging.getLogger("solemate.payments")


class PaymentsNotConfigured(RuntimeError):
    pass


def _client() -> stripe.StripeClient:
    s = get_settings()
    if not s.payments_enabled:
        raise PaymentsNotConfigured("Stripe is not configured (set SOLEMATE_STRIPE_SECRET_KEY).")
    kwargs: dict[str, Any] = {"max_network_retries": 2}
    if s.stripe_api_base:
        kwargs["base_addresses"] = {"api": s.stripe_api_base}
    return stripe.StripeClient(s.stripe_secret_key, **kwargs)


def _describe(selections: dict[str, str]) -> str:
    text = ", ".join(f"{k}: {v.replace('_', ' ')}" for k, v in selections.items())
    return text[:480]


def build_session_params(order: Order, items: list[dict], currency: str) -> dict[str, Any]:

    s = get_settings()
    base = s.public_url.rstrip("/")
    line_items = [
        {
            "quantity": int(i["quantity"]),
            "price_data": {
                "currency": currency.lower(),
                "unit_amount": int(i["unit_cents"]),
                "product_data": {
                    "name": f"{i['shoe_name']} (Preorder)",
                    "description": _describe(i.get("selections", {})),
                },
            },
        }
        for i in items
    ]
    return {
        "mode": "payment",
        "client_reference_id": order.id,
        "customer_email": order.email,
        "line_items": line_items,
        "metadata": {"order_id": order.id, "preorder": "true", "terms_version": order.terms_version or ""},
        "payment_intent_data": {
            "description": f"SoleMate preorder {order.id}",
            "metadata": {"order_id": order.id, "preorder": "true"},
        },
        "custom_text": {
            "submit": {
                "message": (
                    "This is a PREORDER. Your shoes are made to order from your scan and have not been "
                    f"made yet. {s.preorder_ship_estimate}"
                )[:1200]
            }
        },
        "success_url": f"{base}/orders/{order.id}?paid=1",
        "cancel_url": f"{base}/checkout?cancelled=1",
    }


def create_checkout_session(order: Order, items: list[dict], currency: str) -> dict[str, str]:
    session = _client().v1.checkout.sessions.create(params=build_session_params(order, items, currency)).to_dict()
    return {"id": session["id"], "url": session["url"]}


def retrieve_session(session_id: str) -> dict[str, Any]:
    session = _client().v1.checkout.sessions.retrieve(session_id).to_dict()
    return {
        "id": session["id"],
        "payment_status": session.get("payment_status"),
        "status": session.get("status"),
        "amount_total": session.get("amount_total"),
        "currency": session.get("currency"),
        "payment_intent": session.get("payment_intent"),
        "metadata": dict(session.get("metadata") or {}),
    }


def construct_event(payload: bytes, signature: str | None) -> dict[str, Any]:

    secret = get_settings().stripe_webhook_secret
    if not secret:
        raise PaymentsNotConfigured("SOLEMATE_STRIPE_WEBHOOK_SECRET is not set.")
    return stripe.Webhook.construct_event(payload, signature or "", secret).to_dict()
