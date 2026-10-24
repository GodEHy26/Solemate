"""End-to-end API tests using synthetic renders (no real photos needed)."""
import io
from pathlib import Path

import cv2
import numpy as np
import pytest

from tests.synthetic import ellipsoid_surface, paper_scene, write_orbit_frames

# Ellipsoid "foot" in reconstruction units (radius-1 orbit): 0.56 long, 0.20 wide, 0.16 tall, like a real foot ~45 cm from the phone.
RADII = (0.28, 0.10, 0.08)
CENTER = (0.0, 0.0, 0.08)


def _jpeg_bytes(img) -> bytes:
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def _upload_frames(client, scan_id, tmp_path, n_views=16, topdown=True):
    frames = write_orbit_frames(tmp_path / "frames", ellipsoid_surface(CENTER, RADII), n_views=n_views)
    if topdown:
        td = paper_scene(foot_length_mm=260.0, foot_width_mm=100.0)
        r = client.post(
            f"/api/scans/{scan_id}/frames",
            files={"image": ("top.jpg", _jpeg_bytes(td), "image/jpeg")},
            data={"yaw_deg": 0, "pitch_deg": 90, "kind": "topdown"},
        )
        assert r.status_code == 201, r.text
    for f in frames:
        r = client.post(
            f"/api/scans/{scan_id}/frames",
            files={"image": (f["path"].name, Path(f["path"]).read_bytes(), "image/jpeg")},
            data={"yaw_deg": f["yaw_deg"], "pitch_deg": f["pitch_deg"], "kind": "orbit"},
        )
        assert r.status_code == 201, r.text
    return r.json()


def test_health_and_plan(client):
    assert client.get("/api/health").json()["status"] == "ok"
    plan = client.get("/api/scans/plan").json()
    assert plan["sector_count"] == 24
    assert plan["poses"][0]["kind"] == "topdown"


def test_catalog_endpoints(client):
    shoes = client.get("/api/catalog/shoes").json()["shoes"]
    assert len(shoes) >= 1
    detail = client.get(f"/api/catalog/shoes/{shoes[0]['slug']}").json()
    assert detail["components"]
    assert client.get("/api/catalog/shoes/nope").status_code == 404
    comps = client.get("/api/catalog/components").json()
    assert any(c["id"] == "outsole" for c in comps["components"])
    priced = client.post("/api/catalog/price", json={"shoe_slug": shoes[0]["slug"], "selections": shoes[0]["defaults"]}).json()
    assert priced["valid"] and priced["total_cents"] > 0


def test_frame_validation(client):
    scan = client.post("/api/scans", json={"side": "right"}).json()
    r = client.post(
        f"/api/scans/{scan['id']}/frames",
        files={"image": ("bad.jpg", b"not an image", "image/jpeg")},
        data={"yaw_deg": 0, "pitch_deg": 30, "kind": "orbit"},
    )
    assert r.status_code == 422
    r = client.post(f"/api/scans/{scan['id']}/reconstruct")
    assert r.status_code == 422  # not enough frames
    assert client.get("/api/scans/does-not-exist").status_code == 404


def test_full_scan_flow_with_paper_scale(client, tmp_path):
    scan = client.post("/api/scans", json={"side": "left", "paper_size": "A4"}).json()
    state = _upload_frames(client, scan["id"], tmp_path)
    assert state["frame_count"] == 17
    assert state["coverage"]["fraction"] >= 0.6

    r = client.post(f"/api/scans/{scan['id']}/reconstruct")
    assert r.status_code == 202, r.text
    state = client.get(f"/api/scans/{scan['id']}").json()
    assert state["status"] == "complete", state["error"]

    profile = client.get(f"/api/profiles/{state['profile_id']}").json()
    m = profile["measurements"]
    assert profile["scale_method"] == "paper"
    # Scaled so the hull length equals the paper-measured 260 mm; width follows the ellipsoid proportions.
    assert m["length_mm"] == pytest.approx(260.0, rel=0.03)
    assert m["ball_width_mm"] == pytest.approx(100.0, rel=0.20)
    assert m["instep_height_mm"] > 50
    assert m["ball_girth_mm"] and m["ball_girth_mm"] > m["ball_width_mm"] * 2
    assert profile["sizing"]["recommended"]["us_men"] > 0
    assert len(profile["footprint_mm"]) >= 8
    assert profile["sections"]

    glb = client.get(profile["mesh_urls"]["glb"])
    assert glb.status_code == 200 and glb.content[:4] == b"glTF"
    obj = client.get(profile["mesh_urls"]["obj"])
    assert obj.status_code == 200 and b"v " in obj.content

    spec = client.get(f"/api/profiles/{profile['id']}/last-spec", params={"shoe": "solemate-court"}).json()
    assert spec["base_last"]["family"] == "court"
    assert spec["target_mm"]["length_mm"] == pytest.approx(m["length_mm"] + 10, abs=0.2)

    # frames can no longer be added once processed
    r = client.post(
        f"/api/scans/{scan['id']}/frames",
        files={"image": ("x.jpg", _jpeg_bytes(np.zeros((10, 10, 3), np.uint8)), "image/jpeg")},
        data={"yaw_deg": 0, "pitch_deg": 30, "kind": "orbit"},
    )
    assert r.status_code == 409
    return profile


def test_scan_flow_with_known_length(client, tmp_path):
    scan = client.post("/api/scans", json={"side": "right", "known_length_mm": 275}).json()
    _upload_frames(client, scan["id"], tmp_path, topdown=False)
    assert client.post(f"/api/scans/{scan['id']}/reconstruct").status_code == 202
    state = client.get(f"/api/scans/{scan['id']}").json()
    assert state["status"] == "complete", state["error"]
    profile = client.get(f"/api/profiles/{state['profile_id']}").json()
    assert profile["scale_method"] == "known_length"
    assert profile["measurements"]["length_mm"] == pytest.approx(275.0, rel=0.03)


def test_mesh_upload_route(client, tmp_path):
    import trimesh

    mesh = trimesh.creation.icosphere(subdivisions=3)
    mesh.apply_scale([130.0, 48.0, 40.0])
    mesh.apply_translation([0, 0, 40.0])
    path = tmp_path / "foot.glb"
    mesh.export(str(path))
    scan = client.post("/api/scans", json={"side": "left"}).json()
    r = client.post(f"/api/scans/{scan['id']}/mesh", files={"mesh": ("foot.glb", path.read_bytes())}, data={"units": "mm"})
    assert r.status_code == 202, r.text
    state = client.get(f"/api/scans/{scan['id']}").json()
    assert state["status"] == "complete", state["error"]
    profile = client.get(f"/api/profiles/{state['profile_id']}").json()
    assert profile["source"] == "uploaded_mesh"
    assert profile["measurements"]["length_mm"] == pytest.approx(260.0, rel=0.05)


def test_photos_are_deleted_after_reconstruction(client, tmp_path):
    from app.config import get_settings

    scan = client.post("/api/scans", json={"side": "left", "known_length_mm": 270}).json()
    _upload_frames(client, scan["id"], tmp_path, topdown=False)
    frames_dir = get_settings().scans_dir / scan["id"] / "frames"
    assert any(frames_dir.iterdir())
    assert client.post(f"/api/scans/{scan['id']}/reconstruct").status_code == 202
    assert client.get(f"/api/scans/{scan['id']}").json()["status"] == "complete"
    assert not frames_dir.exists()                       # raw photos gone
    assert (get_settings().scans_dir / scan["id"] / "foot.glb").exists()   # model kept


def test_site_config_is_preorder(client):
    cfg = client.get("/api/config").json()
    assert cfg["preorder"] is True
    assert cfg["payments_enabled"] is True
    assert cfg["legal"]["configured"] is True
    assert "ship" in cfg["ship_estimate"].lower()
