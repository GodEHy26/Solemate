
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScanSession(SQLModel, table=True):
    __tablename__ = "scan_sessions"

    id: str = Field(default_factory=_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    side: str = Field(default="left", description="left or right")
    status: str = Field(default="capturing", description="capturing | processing | complete | failed")
    frame_count: int = 0
    frames_json: str = "[]"
    known_length_mm: float | None = None
    paper_size: str | None = None
    error: str | None = None
    warnings_json: str = "[]"
    profile_id: str | None = Field(default=None, index=True)


class FootProfile(SQLModel, table=True):
    __tablename__ = "foot_profiles"

    id: str = Field(default_factory=_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    scan_session_id: str = Field(index=True)
    side: str = "left"
    source: str = Field(default="visual_hull", description="visual_hull | uploaded_mesh")
    scale_method: str = "assumed"
    scale_confidence: str = "low"
    measurements_json: str = "{}"
    sizing_json: str = "{}"
    footprint_json: str = "[]"
    profiles_json: str = "{}"
    sections_json: str = "[]"
    warnings_json: str = "[]"
    confidence: str = "high"
    mesh_glb_path: str | None = None
    mesh_obj_path: str | None = None


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: str = Field(default_factory=_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=_now)
    status: str = Field(default="awaiting_payment", index=True)
    customer_name: str
    email: str
    shipping_json: str = "{}"
    items_json: str = "[]"
    currency: str = "USD"
    subtotal_cents: int = 0
    total_cents: int = 0
    notes: str | None = None
    preorder: bool = True
    terms_version: str | None = None
    terms_accepted_at: datetime | None = None
    checkout_session_id: str | None = Field(default=None, index=True)
    payment_intent_id: str | None = None
    amount_paid_cents: int = 0
    paid_at: datetime | None = None
