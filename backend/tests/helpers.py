"""Shared helpers: build a priced order through the API."""
from __future__ import annotations

import io

import trimesh

SHIPPING = {"line1": "1 Main St", "city": "Seoul", "postal_code": "04524", "country": "KR"}


def make_profile(client, side: str = "left") -> str:
    mesh = trimesh.creation.icosphere(subdivisions=3)
    mesh.apply_scale([130.0, 48.0, 40.0])
    mesh.apply_translation([0, 0, 40.0])
    data = mesh.export(file_type="glb")
    scan = client.post("/api/scans", json={"side": side}).json()
    r = client.post(f"/api/scans/{scan['id']}/mesh", files={"mesh": ("foot.glb", io.BytesIO(data).read())}, data={"units": "mm"})
    assert r.status_code == 202, r.text
    state = client.get(f"/api/scans/{scan['id']}").json()
    assert state["status"] == "complete", state["error"]
    return state["profile_id"]


def order_body(client, left: str | None, right: str | None, accepted: bool = True, quantity: int = 1) -> dict:
    shoes = client.get("/api/catalog/shoes").json()["shoes"]
    daily = next(s for s in shoes if s["slug"] == "solemate-daily")
    return {
        "customer_name": "Test Customer",
        "email": "test@example.com",
        "shipping": SHIPPING,
        "accepted_terms": accepted,
        "items": [
            {"shoe_slug": "solemate-daily", "selections": daily["defaults"], "quantity": quantity,
             "left_profile_id": left, "right_profile_id": right}
        ],
    }
