
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.config import get_settings
from app.database import get_engine
from app.db_models import Order, ScanSession
from app.services.retention import purge_stale
from tests.helpers import make_profile, order_body


def _age(model, ident: str, hours: int, field: str):
    with Session(get_engine()) as db:
        row = db.get(model, ident)
        setattr(row, field, datetime.now(timezone.utc) - timedelta(hours=hours))
        db.add(row); db.commit()


def test_purge_removes_abandoned_scans_and_unpaid_orders_but_keeps_the_rest(client):
    stale = client.post("/api/scans", json={"side": "left"}).json()["id"]
    fresh = client.post("/api/scans", json={"side": "left"}).json()["id"]
    done_profile = make_profile(client, "right")
    done_session = client.get(f"/api/profiles/{done_profile}").json()["scan_session_id"]
    stale_dir = get_settings().scans_dir / stale
    assert stale_dir.exists()
    _age(ScanSession, stale, get_settings().stale_session_hours + 1, "updated_at")
    _age(ScanSession, done_session, 24 * 30, "updated_at")

    left, right = make_profile(client, "left"), make_profile(client, "right")
    old_unpaid = client.post("/api/orders", json=order_body(client, left, right)).json()["id"]
    new_unpaid = client.post("/api/orders", json=order_body(client, left, right)).json()["id"]
    _age(Order, old_unpaid, get_settings().unpaid_order_hours + 1, "created_at")

    with Session(get_engine()) as db:
        removed = purge_stale(db)
    assert removed["sessions"] >= 1 and removed["orders"] >= 1
    assert client.get(f"/api/scans/{stale}").status_code == 404 and not stale_dir.exists()
    assert client.get(f"/api/scans/{fresh}").status_code == 200
    assert client.get(f"/api/profiles/{done_profile}").status_code == 200
    assert client.get(f"/api/orders/{old_unpaid}").status_code == 404
    assert client.get(f"/api/orders/{new_unpaid}").status_code == 200


def test_customer_can_delete_a_scan(client):
    pid = make_profile(client, "left")
    mesh_url = client.get(f"/api/profiles/{pid}").json()["mesh_urls"]["glb"]
    assert client.get(mesh_url).status_code == 200
    assert client.delete(f"/api/profiles/{pid}").status_code == 204
    assert client.get(f"/api/profiles/{pid}").status_code == 404
    assert client.get(mesh_url).status_code == 404


def test_scan_attached_to_an_open_preorder_cannot_be_deleted(client):
    left, right = make_profile(client, "left"), make_profile(client, "right")
    order = client.post("/api/orders", json=order_body(client, left, right)).json()
    r = client.delete(f"/api/profiles/{left}")
    assert r.status_code == 409 and "preorder" in r.text.lower()
    assert client.get(f"/api/profiles/{left}").status_code == 200
    assert order["id"]


def test_additive_migration_adds_missing_order_columns(tmp_path):
    from sqlalchemy import create_engine, inspect, text
    from sqlmodel import SQLModel

    from app import db_models  # noqa: F401
    from app.database import _add_missing_columns

    engine = create_engine(f"sqlite:///{tmp_path/'old.db'}")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE orders (id VARCHAR PRIMARY KEY, created_at DATETIME, status VARCHAR, customer_name VARCHAR, "
                       "email VARCHAR, shipping_json VARCHAR, items_json VARCHAR, currency VARCHAR, subtotal_cents INTEGER, total_cents INTEGER, notes VARCHAR)"))
        c.execute(text("INSERT INTO orders (id, status, customer_name, email) VALUES ('o1', 'pending_payment', 'A', 'a@b.c')"))
    SQLModel.metadata.create_all(engine)
    _add_missing_columns(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("orders")}
    assert {"preorder", "checkout_session_id", "amount_paid_cents", "paid_at", "terms_accepted_at"} <= cols
    with engine.connect() as c:
        row = c.execute(text("SELECT preorder, amount_paid_cents FROM orders WHERE id='o1'")).one()
    assert tuple(row) == (1, 0)
