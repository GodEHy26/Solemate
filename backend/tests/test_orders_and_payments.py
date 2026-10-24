"""Preorders and Stripe: consent, pricing, checkout params, signed webhooks, confirm fallback."""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

import pytest

from app.config import get_settings
from app.services import payments
from tests.helpers import make_profile, order_body

SECRET = "whsec_test_secret"


@pytest.fixture(scope="module")
def profiles(client):
    return make_profile(client, "left"), make_profile(client, "right")


def _new_order(client, profiles, **kw) -> dict:
    r = client.post("/api/orders", json=order_body(client, *profiles, **kw))
    assert r.status_code == 201, r.text
    return r.json()


def _sign(payload: bytes, secret: str = SECRET, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _event(order: dict, *, etype="checkout.session.completed", status="paid", amount=None, currency="usd") -> bytes:
    return json.dumps(
        {
            "id": "evt_1", "object": "event", "type": etype, "api_version": "2024-06-20", "created": int(time.time()),
            "data": {"object": {
                "id": "cs_test_1", "object": "checkout.session", "payment_status": status,
                "amount_total": order["total_cents"] if amount is None else amount, "currency": currency,
                "payment_intent": "pi_123", "client_reference_id": order["id"], "metadata": {"order_id": order["id"]},
            }},
        }
    ).encode()


def _post_event(client, payload: bytes, signature: str | None):
    headers = {"stripe-signature": signature} if signature is not None else {}
    return client.post("/api/stripe/webhook", content=payload, headers=headers)


# ---------------------------------------------------------------- order creation
def test_order_is_a_preorder_awaiting_payment(client, profiles):
    order = _new_order(client, profiles, quantity=2)
    assert order["status"] == "awaiting_payment"
    assert order["preorder"] is True
    assert order["amount_paid_cents"] == 0
    assert "ship" in order["ship_estimate"].lower()
    unit = client.post("/api/catalog/price", json={"shoe_slug": "solemate-daily", "selections": order["items"][0]["selections"]}).json()
    assert order["total_cents"] == 2 * unit["total_cents"]


def test_terms_must_be_accepted(client, profiles):
    r = client.post("/api/orders", json=order_body(client, *profiles, accepted=False))
    assert r.status_code == 422 and "accept" in r.text.lower()
    body = order_body(client, *profiles); del body["accepted_terms"]
    assert client.post("/api/orders", json=body).status_code == 422


def test_both_feet_are_required(client, profiles):
    assert client.post("/api/orders", json=order_body(client, profiles[0], None)).status_code == 422
    assert client.post("/api/orders", json=order_body(client, "nope", "nope")).status_code == 422


# ---------------------------------------------------------------- checkout session parameters
def test_checkout_params_are_priced_by_the_server_and_labelled_preorder(client, profiles):
    from app.db_models import Order
    from app.database import get_engine
    from sqlmodel import Session

    order = _new_order(client, profiles, quantity=2)
    with Session(get_engine()) as db:
        row = db.get(Order, order["id"])
        params = payments.build_session_params(row, json.loads(row.items_json), row.currency)
    assert params["mode"] == "payment"
    assert params["success_url"] == f"https://shop.example.com/orders/{order['id']}?paid=1"
    assert params["cancel_url"].startswith("https://shop.example.com/checkout")
    li = params["line_items"][0]
    assert li["quantity"] == 2 and li["price_data"]["currency"] == "usd"
    assert li["price_data"]["product_data"]["name"].endswith("(Preorder)")
    assert li["price_data"]["unit_amount"] * li["quantity"] == order["total_cents"]
    assert params["metadata"]["order_id"] == order["id"]
    assert "PREORDER" in params["custom_text"]["submit"]["message"]


class _FakeStripe(BaseHTTPRequestHandler):
    seen: list[tuple[str, str, dict]] = []

    def _reply(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        _FakeStripe.seen.append(("POST", self.path, parse_qs(body)))
        self._reply({"id": "cs_test_fake", "object": "checkout.session", "url": "https://checkout.stripe.test/pay/cs_test_fake"})

    def do_GET(self):
        _FakeStripe.seen.append(("GET", self.path, {}))
        self._reply({"id": "cs_test_fake", "object": "checkout.session", "payment_status": "paid", "status": "complete",
                     "amount_total": _FakeStripe.amount, "currency": "usd", "payment_intent": "pi_fake",
                     "metadata": {"order_id": _FakeStripe.order_id}})

    def log_message(self, *a):  # silence
        pass

    amount = 0
    order_id = ""


@pytest.fixture
def fake_stripe(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _FakeStripe)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _FakeStripe.seen.clear()
    monkeypatch.setattr(get_settings(), "stripe_api_base", f"http://127.0.0.1:{server.server_port}")
    yield _FakeStripe
    server.shutdown()


def test_checkout_endpoint_talks_to_stripe_sdk_correctly(client, profiles, fake_stripe):
    order = _new_order(client, profiles)
    r = client.post(f"/api/orders/{order['id']}/checkout")
    assert r.status_code == 200, r.text
    assert r.json()["url"] == "https://checkout.stripe.test/pay/cs_test_fake"
    method, path, form = fake_stripe.seen[-1]
    assert (method, path) == ("POST", "/v1/checkout/sessions")
    assert form["mode"] == ["payment"]
    assert form["line_items[0][price_data][product_data][name]"][0].endswith("(Preorder)")
    assert form["line_items[0][price_data][unit_amount]"] == [str(order["total_cents"])]
    assert form["metadata[order_id]"] == [order["id"]]
    assert form["customer_email"] == ["test@example.com"]
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "awaiting_payment"  # not paid until Stripe says so


def test_confirm_marks_paid_only_when_stripe_says_paid_and_amount_matches(client, profiles, fake_stripe):
    order = _new_order(client, profiles)
    client.post(f"/api/orders/{order['id']}/checkout")
    fake_stripe.order_id, fake_stripe.amount = order["id"], order["total_cents"]
    out = client.post(f"/api/orders/{order['id']}/confirm").json()
    assert out["status"] == "preordered" and out["amount_paid_cents"] == order["total_cents"]
    assert out["paid_at"]


def test_confirm_with_wrong_amount_goes_to_review(client, profiles, fake_stripe):
    order = _new_order(client, profiles)
    client.post(f"/api/orders/{order['id']}/checkout")
    fake_stripe.order_id, fake_stripe.amount = order["id"], order["total_cents"] - 1
    out = client.post(f"/api/orders/{order['id']}/confirm").json()
    assert out["status"] == "needs_review" and out["amount_paid_cents"] == 0


def test_checkout_unavailable_without_keys(client, profiles, monkeypatch):
    order = _new_order(client, profiles)
    monkeypatch.setattr(get_settings(), "stripe_secret_key", "")
    r = client.post(f"/api/orders/{order['id']}/checkout")
    assert r.status_code == 503 and "not been charged" in r.text
    assert client.get("/api/config").json()["payments_enabled"] is False


# ---------------------------------------------------------------- webhook
def test_webhook_rejects_bad_or_missing_signature(client, profiles):
    order = _new_order(client, profiles)
    payload = _event(order)
    assert _post_event(client, payload, None).status_code == 400
    assert _post_event(client, payload, _sign(payload, "whsec_wrong")).status_code == 400
    assert _post_event(client, payload, _sign(payload, ts=int(time.time()) - 3600)).status_code == 400   # replay window
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "awaiting_payment"


def test_webhook_marks_preorder_paid_and_is_idempotent(client, profiles):
    order = _new_order(client, profiles)
    payload = _event(order)
    assert _post_event(client, payload, _sign(payload)).status_code == 200
    got = client.get(f"/api/orders/{order['id']}").json()
    assert got["status"] == "preordered" and got["amount_paid_cents"] == order["total_cents"]
    paid_at = got["paid_at"]
    assert _post_event(client, payload, _sign(payload)).status_code == 200      # Stripe retries
    assert client.get(f"/api/orders/{order['id']}").json()["paid_at"] == paid_at


def test_webhook_ignores_unpaid_and_amount_mismatch(client, profiles):
    unpaid = _new_order(client, profiles)
    p = _event(unpaid, status="unpaid")
    _post_event(client, p, _sign(p))
    assert client.get(f"/api/orders/{unpaid['id']}").json()["status"] == "awaiting_payment"

    wrong = _new_order(client, profiles)
    p = _event(wrong, amount=1)
    _post_event(client, p, _sign(p))
    got = client.get(f"/api/orders/{wrong['id']}").json()
    assert got["status"] == "needs_review" and got["amount_paid_cents"] == 0

    p = _event(unpaid, currency="eur", status="paid")
    _post_event(client, p, _sign(p))
    assert client.get(f"/api/orders/{unpaid['id']}").json()["status"] == "needs_review"


def test_webhook_unknown_order_and_failed_payment(client, profiles):
    ghost = {"id": "does-not-exist", "total_cents": 1}
    p = _event(ghost)
    assert _post_event(client, p, _sign(p)).json() == {"received": True, "handled": False}
    order = _new_order(client, profiles)
    p = _event(order, etype="checkout.session.async_payment_failed", status="unpaid")
    _post_event(client, p, _sign(p))
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "payment_failed"
    r = client.post(f"/api/orders/{order['id']}/checkout")   # can retry after a failure
    assert r.status_code in (200, 502)


def test_paid_order_cannot_be_checked_out_again(client, profiles):
    order = _new_order(client, profiles)
    p = _event(order); _post_event(client, p, _sign(p))
    assert client.post(f"/api/orders/{order['id']}/checkout").status_code == 409
