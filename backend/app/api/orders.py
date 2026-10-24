"""Preorders: server-side pricing, consent record, Stripe Checkout and payment confirmation.

Lifecycle: ``awaiting_payment`` -> ``preordered`` (paid). Anything the customer never pays for is
deleted by the retention job after ``unpaid_order_hours``.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..config import get_settings
from ..database import get_session
from ..db_models import FootProfile, Order
from ..schemas import OrderCreate, OrderOut
from ..services import payments
from ..services.catalog.loader import get_shoe
from ..services.catalog.pricing import price_configuration

router = APIRouter(prefix="/api/orders", tags=["orders"])
log = logging.getLogger("solemate.orders")

PAYABLE = ("awaiting_payment", "payment_failed")


def _to_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        status=order.status,
        customer_name=order.customer_name,
        email=order.email,
        shipping=json.loads(order.shipping_json),
        items=json.loads(order.items_json),
        currency=order.currency,
        subtotal_cents=order.subtotal_cents,
        total_cents=order.total_cents,
        notes=order.notes,
        created_at=order.created_at,
        preorder=order.preorder,
        amount_paid_cents=order.amount_paid_cents,
        paid_at=order.paid_at,
        ship_estimate=get_settings().preorder_ship_estimate,
    )


def _load(db: Session, order_id: str) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "order not found")
    return order


def apply_paid_session(db: Session, order: Order, session: dict) -> bool:
    """Mark an order as paid from a Stripe Checkout session. Idempotent; returns True if it changed.

    The amount and currency Stripe actually charged must equal what we priced, otherwise the order
    is parked as ``needs_review`` instead of silently accepted.
    """
    if session.get("payment_status") != "paid" or order.status == "preordered":
        return False
    if order.status not in PAYABLE + ("needs_review",):
        log.warning("order %s is %s; ignoring payment event", order.id, order.status)
        return False
    amount, currency = session.get("amount_total"), (session.get("currency") or "").upper()
    if amount != order.total_cents or currency != order.currency.upper():
        log.error("order %s amount mismatch: stripe %s %s vs expected %s %s", order.id, amount, currency, order.total_cents, order.currency)
        order.status = "needs_review"
    else:
        order.status = "preordered"
        order.amount_paid_cents = int(amount)
        order.paid_at = datetime.now(timezone.utc)
    intent = session.get("payment_intent")
    order.payment_intent_id = intent if isinstance(intent, str) else getattr(intent, "id", None) or order.payment_intent_id
    db.add(order)
    db.commit()
    return order.status == "preordered"


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_session)) -> OrderOut:
    settings = get_settings()
    if not payload.accepted_terms:
        raise HTTPException(422, "You must accept the preorder terms and privacy policy to place a preorder.")
    items = []
    subtotal = 0
    currency = "USD"
    for i, item in enumerate(payload.items):
        shoe = get_shoe(item.shoe_slug)
        if shoe is None:
            raise HTTPException(422, f"item {i}: unknown shoe '{item.shoe_slug}'")
        priced = price_configuration(shoe, item.selections)
        if not priced.valid:
            raise HTTPException(422, f"item {i}: " + " ".join(priced.errors))
        for label, pid in (("left", item.left_profile_id), ("right", item.right_profile_id)):
            if pid is not None and db.get(FootProfile, pid) is None:
                raise HTTPException(422, f"item {i}: {label} foot profile '{pid}' not found")
        if not (item.left_profile_id and item.right_profile_id):
            raise HTTPException(422, f"item {i}: every shoe is made from your scan, so both feet must be scanned first")
        currency = priced.currency
        line_total = priced.total_cents * item.quantity
        subtotal += line_total
        items.append(
            {
                "shoe_slug": shoe["slug"],
                "shoe_name": shoe["name"],
                "selections": item.selections,
                "colors": item.colors,
                "quantity": item.quantity,
                "left_profile_id": item.left_profile_id,
                "right_profile_id": item.right_profile_id,
                "unit_cents": priced.total_cents,
                "line_cents": line_total,
                "price_lines": [l.to_dict() for l in priced.lines],
            }
        )
    order = Order(
        customer_name=payload.customer_name,
        email=str(payload.email),
        shipping_json=json.dumps(payload.shipping.model_dump()),
        items_json=json.dumps(items),
        currency=currency,
        subtotal_cents=subtotal,
        total_cents=subtotal,  # shipping and tax are not charged yet; see docs/PAYMENTS.md
        notes=payload.notes,
        preorder=True,
        terms_version=settings.terms_version,
        terms_accepted_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _to_out(order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_session)) -> OrderOut:
    return _to_out(_load(db, order_id))


@router.post("/{order_id}/checkout")
def start_checkout(order_id: str, db: Session = Depends(get_session)) -> dict:
    """Create a Stripe Checkout session for the order and return the hosted payment page URL."""
    order = _load(db, order_id)
    if order.status not in PAYABLE:
        raise HTTPException(409, f"order is {order.status}; it cannot be paid again")
    if not get_settings().payments_enabled:
        raise HTTPException(503, "Payments are not switched on yet. Your preorder has not been charged.")
    try:
        session = payments.create_checkout_session(order, json.loads(order.items_json), order.currency)
    except stripe.StripeError as exc:
        log.exception("stripe checkout failed for order %s", order.id)
        raise HTTPException(502, "The payment provider rejected the request. Please try again.") from exc
    order.checkout_session_id = session["id"]
    db.add(order)
    db.commit()
    return {"url": session["url"], "session_id": session["id"]}


@router.post("/{order_id}/confirm", response_model=OrderOut)
def confirm_payment(order_id: str, db: Session = Depends(get_session)) -> OrderOut:
    """Ask Stripe directly whether this order was paid. Safety net for a slow or missing webhook."""
    order = _load(db, order_id)
    if order.status in PAYABLE and order.checkout_session_id and get_settings().payments_enabled:
        try:
            session = payments.retrieve_session(order.checkout_session_id)
        except stripe.StripeError:
            log.exception("could not retrieve session for order %s", order.id)
            raise HTTPException(502, "Could not reach the payment provider. Try again in a moment.")
        if session["metadata"].get("order_id") == order.id:
            apply_paid_session(db, order, session)
            db.refresh(order)
    return _to_out(order)
