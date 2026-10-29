

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from ..database import get_session
from ..db_models import Order
from ..services import payments
from .orders import apply_paid_session

router = APIRouter(prefix="/api/stripe", tags=["payments"])
log = logging.getLogger("solemate.webhook")


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_session)) -> dict:
    payload = await request.body()
    try:
        event = payments.construct_event(payload, request.headers.get("stripe-signature"))
    except payments.PaymentsNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, "invalid webhook signature") from exc

    etype = event["type"]
    obj = event["data"]["object"]
    order_id = (obj.get("metadata") or {}).get("order_id") or obj.get("client_reference_id")
    order = db.get(Order, order_id) if order_id else None
    if order is None:
        return {"received": True, "handled": False}

    if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        apply_paid_session(
            db,
            order,
            {
                "payment_status": obj.get("payment_status"),
                "amount_total": obj.get("amount_total"),
                "currency": obj.get("currency"),
                "payment_intent": obj.get("payment_intent"),
            },
        )
    elif etype == "checkout.session.async_payment_failed" and order.status == "awaiting_payment":
        order.status = "payment_failed"
        db.add(order)
        db.commit()
    return {"received": True, "handled": True}
