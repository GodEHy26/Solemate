"""Orders: server-side re-pricing and persistence. Payment is a roadmap item."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..database import get_session
from ..db_models import FootProfile, Order
from ..schemas import OrderCreate, OrderOut
from ..services.catalog.loader import get_shoe
from ..services.catalog.pricing import price_configuration

router = APIRouter(prefix="/api/orders", tags=["orders"])


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
    )


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_session)) -> OrderOut:
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
        if priced.requires_scan and not (item.left_profile_id and item.right_profile_id):
            raise HTTPException(422, f"item {i}: this configuration needs a scan of both feet")
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
        total_cents=subtotal,  # shipping / tax to be added with the payment integration
        notes=payload.notes,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _to_out(order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_session)) -> OrderOut:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "order not found")
    return _to_out(order)
