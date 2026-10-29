"""Request / response models for the HTTP API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

Side = Literal["left", "right"]


# Scans ---------------------------------------------------------------------
class ScanCreate(BaseModel):
    side: Side = "left"
    known_length_mm: float | None = Field(default=None, gt=100, lt=400)
    paper_size: Literal["A4", "LETTER", "A3"] | None = None


class FrameOut(BaseModel):
    index: int
    kind: str
    yaw_deg: float
    pitch_deg: float


class CoverageOut(BaseModel):
    fraction: float
    missing_sectors: list[int]
    largest_gap_deg: float
    sector_count: int


class WarningOut(BaseModel):
    code: str
    severity: Literal["block", "warn"]
    message: str
    fix: str
    details: dict[str, Any] = Field(default_factory=dict)
    side: str | None = None


class ScanOut(BaseModel):
    id: str
    side: str
    status: str
    frame_count: int
    frames: list[FrameOut]
    coverage: CoverageOut
    known_length_mm: float | None
    paper_size: str | None
    error: str | None
    warnings: list[WarningOut] = Field(default_factory=list)
    profile_id: str | None
    created_at: datetime
    updated_at: datetime


# Profiles ------------------------------------------------------------------
class ProfileOut(BaseModel):
    id: str
    scan_session_id: str
    side: str
    source: str
    scale_method: str
    scale_confidence: str
    measurements: dict[str, Any]
    sizing: dict[str, Any]
    footprint_mm: list[list[float]]
    width_profile: list[dict[str, Any]]
    height_profile: list[dict[str, Any]]
    topdown: dict[str, Any] | None
    sections: list[dict[str, Any]]
    warnings: list[WarningOut]
    confidence: Literal["high", "medium", "low"]
    size: dict[str, Any]
    mesh_urls: dict[str, str]
    created_at: datetime


# Configurator --------------------------------------------------------------
class PriceRequest(BaseModel):
    shoe_slug: str
    selections: dict[str, str]


# Orders --------------------------------------------------------------------
class OrderItemIn(BaseModel):
    shoe_slug: str
    selections: dict[str, str]
    colors: dict[str, str] = Field(default_factory=dict)
    quantity: int = Field(default=1, ge=1, le=10)
    left_profile_id: str | None = None
    right_profile_id: str | None = None


class ShippingAddress(BaseModel):
    line1: str
    line2: str | None = None
    city: str
    region: str | None = None
    postal_code: str
    country: str


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    shipping: ShippingAddress
    items: list[OrderItemIn] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=2000)
    accepted_scan_warnings: bool = Field(default=False, description="Customer ticked 'I understand the scan may be less accurate'")
    accepted_terms: bool = Field(description="Customer ticked the preorder terms and privacy policy box")


class OrderOut(BaseModel):
    id: str
    status: str
    customer_name: str
    email: str
    shipping: dict[str, Any]
    items: list[dict[str, Any]]
    currency: str
    subtotal_cents: int
    total_cents: int
    notes: str | None
    created_at: datetime
    preorder: bool = True
    amount_paid_cents: int = 0
    paid_at: datetime | None = None
    ship_estimate: str = ""
