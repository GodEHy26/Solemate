"""Public site configuration: preorder wording and the operator details shown on legal pages."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/config")
def site_config() -> dict:
    s = get_settings()
    return {
        "preorder": True,
        "ship_estimate": s.preorder_ship_estimate,
        "shipping_policy": s.shipping_policy,
        "payments_enabled": s.payments_enabled,
        "terms_version": s.terms_version,
        "legal": {
            "configured": s.legal_configured,
            "company_name": s.company_name,
            "support_email": s.support_email,
            "company_address": s.company_address,
            "governing_law": s.governing_law,
            "stale_session_hours": s.stale_session_hours,
            "unpaid_order_hours": s.unpaid_order_hours,
        },
    }
