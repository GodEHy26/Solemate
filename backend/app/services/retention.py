
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from ..config import get_settings
from ..db_models import Order, ScanSession
from .scanning.pipeline import delete_session_files

log = logging.getLogger("solemate.retention")
OPEN_ORDER_STATUSES = ("awaiting_payment", "preordered", "needs_review", "in_production")


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


def _cutoff(hours: int) -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)


def purge_stale(db: Session) -> dict[str, int]:

    s = get_settings()
    removed = {"sessions": 0, "orders": 0}

    cut = _cutoff(s.stale_session_hours)
    for sess in db.exec(select(ScanSession).where(ScanSession.status != "complete")).all():
        if _naive_utc(sess.updated_at) < cut:
            delete_session_files(sess.id)
            db.delete(sess)
            removed["sessions"] += 1

    cut = _cutoff(s.unpaid_order_hours)
    for order in db.exec(select(Order).where(Order.status == "awaiting_payment")).all():
        if _naive_utc(order.created_at) < cut:
            db.delete(order)
            removed["orders"] += 1

    db.commit()
    if any(removed.values()):
        log.info("retention purge removed %s", removed)
    return removed


def profile_in_open_order(db: Session, profile_id: str) -> bool:
    for order in db.exec(select(Order).where(Order.status.in_(OPEN_ORDER_STATUSES))).all():
        if profile_id in order.items_json:
            return True
    return False
