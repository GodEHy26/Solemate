"""Create demo foot scans on a running SoleMate API, for portfolio screenshots.

Uses the same synthetic test foot as the test suite (an ellipsoid, not a real foot), sent through
the real API as photos so every stage runs: segmentation, visual hull, mesh, measurements, checks.

    backend/.venv/bin/python scripts/portfolio/seed_demo.py            # API on http://localhost:8000

Writes portfolio-shots/profiles.json for capture.mjs.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import cv2  # noqa: E402

from tests.synthetic_scenarios import (  # noqa: E402
    full_ring, orbit_frames, ring_with_gap, topdown_with_paper, topdown_without_paper,
)


def _multipart(fields: dict, file_field: str, filename: str, content: bytes) -> tuple[bytes, str]:
    b = "----solemate-portfolio"
    body = b"".join(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode() for k, v in fields.items())
    body += (f"--{b}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
             "Content-Type: image/jpeg\r\n\r\n").encode() + content + f"\r\n--{b}--\r\n".encode()
    return body, f"multipart/form-data; boundary={b}"


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, path: str, body=None, method: str = "POST", raw: tuple[bytes, str] | None = None) -> dict:
        if raw:
            req = urllib.request.Request(self.base + path, raw[0], {"Content-Type": raw[1]}, method="POST")
        elif body is not None:
            req = urllib.request.Request(self.base + path, json.dumps(body).encode(), {"Content-Type": "application/json"}, method=method)
        else:
            req = urllib.request.Request(self.base + path, method=method)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)

    def scan(self, side: str, yaws: list[float], top: str | None) -> str:
        s = self.call("/api/scans", {"side": side, "paper_size": "A4"})
        if top:
            img = topdown_with_paper() if top == "paper" else topdown_without_paper()
            ok, buf = cv2.imencode(".jpg", img)
            self.call(f"/api/scans/{s['id']}/frames", raw=_multipart({"yaw_deg": 0, "pitch_deg": 90, "kind": "topdown"}, "image", "top.jpg", buf.tobytes()))
        for f in orbit_frames(Path(tempfile.mkdtemp()), yaws):
            self.call(f"/api/scans/{s['id']}/frames", raw=_multipart(
                {"yaw_deg": f["yaw_deg"], "pitch_deg": f["pitch_deg"], "kind": "orbit"}, "image", "o.jpg", f["path"].read_bytes()))
        self.call(f"/api/scans/{s['id']}/reconstruct", {})
        for _ in range(180):
            state = self.call(f"/api/scans/{s['id']}", method="GET")
            if state["status"] in ("complete", "failed"):
                break
            time.sleep(1)
        if not state.get("profile_id"):
            raise SystemExit(f"{side} scan did not complete: {state.get('error')}")
        print(f"  {side:<5} {state['status']}  warnings: {[w['code'] for w in state['warnings']] or 'none'}")
        return state["profile_id"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--out", default=str(ROOT / "portfolio-shots"))
    args = ap.parse_args()
    api = Api(args.api)
    api.call("/api/health", method="GET")
    print("Building demo scans (each takes a few seconds)...")
    profiles = {
        "clean": {"left": api.scan("left", full_ring(), "paper"), "right": api.scan("right", full_ring(), "paper")},
        "warning": api.scan("right", ring_with_gap(150, 240), "paper"),   # heel side missed
        "blocked": api.scan("right", full_ring(), "no-paper"),             # no sheet of paper
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "profiles.json").write_text(json.dumps(profiles, indent=2))
    print(f"Saved {out / 'profiles.json'}")


if __name__ == "__main__":
    main()
