"""Scan quality warnings: each check fires on its symptom, and a clean scan raises nothing."""
from __future__ import annotations

import io
from pathlib import Path

import cv2
import pytest
import trimesh

from app.services.fitting.fit_check import pair_check, size_summary
from app.services.scanning.quality import (
    BLOCK, THRESHOLDS, WARN, FrameStat, ScanWarning, check_agreement, check_background, check_left_right,
    check_orbit, check_scale, confidence, largest_gap_center, side_of,
)
from tests.helpers import SHIPPING
from tests.synthetic_scenarios import (
    full_ring, orbit_frames, ring_with_gap, topdown_with_paper, topdown_without_paper, FOOT_WIDTH_MM,
)


# ============================================================ unit: individual checks
def test_side_names_follow_the_yaw_convention():
    assert side_of(0) == "toe end" and side_of(350) == "toe end"
    assert side_of(90) == "left side" and side_of(180) == "heel end" and side_of(270) == "right side"
    assert side_of(largest_gap_center(ring_with_gap(150, 240))) == "heel end"


@pytest.mark.parametrize("yaws,fires", [
    (full_ring(15), False),
    (full_ring(20), False),                     # 18 frames, every 20 deg: all sectors-ish, small gaps
    (ring_with_gap(150, 240), True),            # 105 deg gap
    (ring_with_gap(150, 195), False),           # 60 deg gap is the limit, 75 % coverage
    (full_ring(30), True),                      # 12 frames: 50 % coverage
])
def test_orbit_thresholds(yaws, fires):
    w = check_orbit(yaws, 15.0)
    assert bool(w) is fires
    if w:
        assert w[0].code == "incomplete_orbit" and w[0].severity == WARN and w[0].fix.startswith("Retake the scan from the ")


@pytest.mark.parametrize("method,blocks", [("paper", False), ("sensor", False), ("known_length", True), ("assumed", True)])
def test_scale_blocks_without_paper(method, blocks):
    w = check_scale(method)
    assert bool(w) is blocks
    if w:
        assert w[0].severity == BLOCK and "paper" in w[0].message


def _frames(areas, methods=None):
    methods = methods or ["otsu"] * len(areas)
    return [FrameStat(i * 15.0, m, a, m != "none") for i, (a, m) in enumerate(zip(areas, methods))]


def test_background_quiet_on_smooth_outlines():
    smooth = [0.10 + 0.03 * abs((i % 12) - 6) / 6 for i in range(24)]   # natural size change around the ring
    assert check_background(_frames(smooth)) == []
    one_fallback = ["otsu"] * 23 + ["grabcut"]
    assert check_background(_frames(smooth, one_fallback)) == []          # a single fallback is tolerated


def test_background_fires_on_fallbacks_or_size_jumps():
    flat = [0.1] * 24
    methods = ["saturation"] * 6 + ["otsu"] * 18                           # 25 % fallbacks
    assert check_background(_frames(flat, methods))[0].code == "confusing_background"
    spiky = flat.copy(); spiky[5] = 0.2                                    # one frame doubles: two jumps
    w = check_background(_frames(spiky))
    assert w and w[0].details["size_jumps"] == 2


def test_agreement_allows_one_voxel_then_three_percent():
    assert check_agreement(None, 95.0, 2.0) == []
    assert check_agreement(94.0, 95.0, 2.0) == []                          # inside the voxel interval
    assert check_agreement(95.0 * 1.029, 95.0, 2.0) == []                  # just under 3 % above
    w = check_agreement(95.0 * 1.04, 95.0, 2.0)
    assert w and w[0].code == "measurements_disagree" and w[0].severity == WARN


def test_left_right_threshold():
    assert check_left_right(260, 260 + THRESHOLDS["left_right_mm"]) == []
    w = check_left_right(260, 269)
    assert w and w[0].severity == WARN and w[0].details["longer"] == "right"


def test_confidence_levels():
    assert confidence([]) == "high"
    assert confidence(check_left_right(250, 270)) == "medium"
    assert confidence(check_scale("assumed") + check_left_right(250, 270)) == "low"


# ============================================================ unit: size output
def test_size_single_range_none():
    single = size_summary(265.0, 100.0, [])
    assert single["mode"] == "single"
    assert single["sizes"]["us_men"]["low"] == single["sizes"]["us_men"]["high"]

    rng = size_summary(265.0, 100.0, check_left_right(250, 270))
    us = rng["sizes"]["us_men"]
    assert rng["mode"] == "range" and us["high"] - us["low"] == 0.5
    assert "warning" in rng["explanation"]
    assert us["low"] <= single["sizes"]["us_men"]["low"] <= us["high"]

    none = size_summary(265.0, 100.0, check_scale("assumed"))
    assert none["mode"] == "none" and none["sizes"] is None and "top-down photo" in none["explanation"]


def test_pair_uses_longer_foot_and_tags_sides():
    left = {"length_mm": 262.0, "ball_width_mm": 100.0, "warnings": []}
    right = {"length_mm": 266.0, "ball_width_mm": 101.0, "warnings": check_orbit(ring_with_gap(150, 240), 15)}
    out = pair_check(left, right)
    assert out["confidence"] == "medium" and out["needs_acknowledgement"] and not out["blocked"]
    assert [w["side"] for w in out["warnings"]] == ["right"]
    assert out["size"]["mode"] == "range"
    assert out["size"]["sizes"]["us_men"] == size_summary(266.0, 101.0, [ScanWarning("x", WARN, "m", "f")])["sizes"]["us_men"]


# ============================================================ end to end: synthetic scans through the API
def _jpeg(img) -> bytes:
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def _scan(client, tmp_path: Path, yaws, floor="plain", top="paper", width=None, side="left", known=None) -> dict:
    body = {"side": side, "paper_size": "A4"}
    if known:
        body["known_length_mm"] = known
    scan = client.post("/api/scans", json=body).json()
    if top:
        img = topdown_with_paper(width or FOOT_WIDTH_MM) if top == "paper" else topdown_without_paper()
        r = client.post(f"/api/scans/{scan['id']}/frames", files={"image": ("top.jpg", _jpeg(img), "image/jpeg")},
                        data={"yaw_deg": 0, "pitch_deg": 90, "kind": "topdown"})
        assert r.status_code == 201, r.text
    for f in orbit_frames(tmp_path / scan["id"], yaws, floor):
        r = client.post(f"/api/scans/{scan['id']}/frames", files={"image": ("o.jpg", f["path"].read_bytes(), "image/jpeg")},
                        data={"yaw_deg": f["yaw_deg"], "pitch_deg": f["pitch_deg"], "kind": "orbit"})
        assert r.status_code == 201, r.text
    assert client.post(f"/api/scans/{scan['id']}/reconstruct").status_code == 202
    state = client.get(f"/api/scans/{scan['id']}").json()
    state["profile"] = client.get(f"/api/profiles/{state['profile_id']}").json() if state["profile_id"] else None
    return state


def _codes(warnings):
    return sorted(w["code"] for w in warnings)


def test_clean_scan_raises_no_warnings(client, tmp_path):
    state = _scan(client, tmp_path, full_ring())
    p = state["profile"]
    assert state["status"] == "complete"
    assert p["warnings"] == [] and state["warnings"] == []
    assert p["confidence"] == "high"
    assert p["size"]["mode"] == "single"


def test_low_coverage_warns_and_names_the_missing_side(client, tmp_path):
    state = _scan(client, tmp_path, ring_with_gap(150, 240))
    p = state["profile"]
    assert _codes(p["warnings"]) == ["incomplete_orbit"]
    w = p["warnings"][0]
    assert w["severity"] == "warn" and w["fix"] == "Retake the scan from the heel end."
    assert p["confidence"] == "medium" and p["size"]["mode"] == "range"


@pytest.mark.parametrize("known", [None, 265])
def test_missing_paper_blocks_the_size(client, tmp_path, known):
    state = _scan(client, tmp_path, full_ring(), top="no-paper", known=known)
    p = state["profile"]
    assert p["scale_method"] == ("known_length" if known else "assumed")
    assert _codes(p["warnings"]) == ["paper_not_found"]
    assert p["warnings"][0]["severity"] == "block"
    assert p["confidence"] == "low"
    assert p["size"]["mode"] == "none" and p["size"]["sizes"] is None


def test_tiled_floor_warns_about_the_background(client, tmp_path):
    state = _scan(client, tmp_path, full_ring(), floor="tiles")
    assert state["status"] == "complete"
    assert "confusing_background" in _codes(state["profile"]["warnings"])


def test_patterned_floor_warns_even_when_the_scan_fails(client, tmp_path):
    state = _scan(client, tmp_path, full_ring(), floor="blotches")
    warnings = state["profile"]["warnings"] if state["profile"] else state["warnings"]
    assert "confusing_background" in _codes(warnings)
    if state["status"] == "failed":                 # the failure must explain itself
        assert state["warnings"][0]["fix"] == "Retake on a plain floor that contrasts with your skin."


def test_paper_and_model_disagree(client, tmp_path):
    state = _scan(client, tmp_path, full_ring(), width=FOOT_WIDTH_MM * 1.12)
    p = state["profile"]
    assert _codes(p["warnings"]) == ["measurements_disagree"]
    assert p["warnings"][0]["details"]["difference_pct"] > 3


# ============================================================ pair check + ordering
def _mesh_profile(client, side: str, length_mm: float) -> str:
    mesh = trimesh.creation.icosphere(subdivisions=3)
    mesh.apply_scale([length_mm / 2, 48.0, 40.0])
    mesh.apply_translation([0, 0, 40.0])
    scan = client.post("/api/scans", json={"side": side}).json()
    r = client.post(f"/api/scans/{scan['id']}/mesh", files={"mesh": ("f.glb", io.BytesIO(mesh.export(file_type="glb")).read())}, data={"units": "mm"})
    assert r.status_code == 202
    return client.get(f"/api/scans/{scan['id']}").json()["profile_id"]


def test_fit_check_left_right(client):
    a, b, c = _mesh_profile(client, "left", 260), _mesh_profile(client, "right", 265), _mesh_profile(client, "right", 275)
    ok = client.get("/api/profiles/fit-check", params={"left": a, "right": b}).json()
    assert ok["warnings"] == [] and ok["confidence"] == "high" and ok["size"]["mode"] == "single"
    far = client.get("/api/profiles/fit-check", params={"left": a, "right": c}).json()
    assert _codes(far["warnings"]) == ["left_right_mismatch"]
    assert far["needs_acknowledgement"] and not far["blocked"] and far["size"]["mode"] == "range"
    assert client.get("/api/profiles/fit-check", params={"left": a, "right": "nope"}).status_code == 404


def _order(client, left, right, ack=False):
    shoes = client.get("/api/catalog/shoes").json()["shoes"]
    daily = next(s for s in shoes if s["slug"] == "solemate-daily")
    return client.post("/api/orders", json={
        "customer_name": "T", "email": "t@example.com", "shipping": SHIPPING, "accepted_terms": True,
        "accepted_scan_warnings": ack,
        "items": [{"shoe_slug": "solemate-daily", "selections": daily["defaults"], "left_profile_id": left, "right_profile_id": right}],
    })


def test_orders_respect_warnings(client, tmp_path):
    a, far = _mesh_profile(client, "left", 260), _mesh_profile(client, "right", 275)
    r = _order(client, a, far)                                        # warn, not acknowledged
    assert r.status_code == 422 and "less accurate" in r.text
    r = _order(client, a, far, ack=True)                              # warn, acknowledged
    assert r.status_code == 201
    item = r.json()["items"][0]
    assert item["scan_confidence"] == "medium" and item["scan_warning_codes"] == ["left_right_mismatch"]
    assert item["scan_warnings_acknowledged"] is True

    blocked = _scan(client, tmp_path, full_ring(), top="no-paper", side="right")["profile_id"]
    r = _order(client, a, blocked, ack=True)                          # block: acknowledgement doesn't help
    assert r.status_code == 422 and "top-down photo" in r.text

    clean_right = _mesh_profile(client, "right", 262)
    r = _order(client, a, clean_right)                                # no warnings: no tick needed
    assert r.status_code == 201 and r.json()["items"][0]["scan_warning_codes"] == []
