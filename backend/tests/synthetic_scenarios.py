"""Synthetic capture scenarios for the quality checks (clean, gaps, no paper, busy floors)."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from tests.synthetic import ellipsoid_surface, orbit_rig, paper_scene, render_silhouette

RADII = (0.28, 0.10, 0.08)          # reconstruction units: a foot about 45 cm from the phone
CENTER = (0.0, 0.0, 0.08)
FOOT_LENGTH_MM = 260.0
FOOT_WIDTH_MM = FOOT_LENGTH_MM * RADII[1] / RADII[0]   # paper photo consistent with the 3D shape
SKIN = (70, 60, 55)


def _floor(kind: str, i: int, h: int, w: int) -> np.ndarray:
    rng = np.random.default_rng(100 + i)
    if kind == "plain":
        return np.full((h, w, 3), 225, np.uint8)
    if kind == "tiles":  # checkerboard rug with dark tiles; shifts as the camera moves
        s, off = 40, (i * 13) % 40
        yy, xx = np.mgrid[0:h, 0:w]
        img = np.empty((h, w, 3), np.uint8)
        light = (((xx + off) // s + (yy // s)) % 2) == 0
        img[light] = (225, 225, 225)
        img[~light] = (80, 70, 65)
        return img
    if kind == "blotches":  # patterned floor: big patches incl. skin-like and dark tones
        img = np.full((h, w, 3), 200, np.uint8)
        palette = [SKIN, (120, 150, 200), (40, 40, 40), (200, 200, 200), (90, 120, 170)]
        for _ in range(14):
            cv2.circle(img, (int(rng.integers(0, w)), int(rng.integers(0, h))), int(rng.integers(25, 70)),
                       palette[int(rng.integers(0, len(palette)))], -1)
        return img
    raise ValueError(kind)


def orbit_frames(out_dir: Path, yaws: list[float], floor: str = "plain", pitch: float = 30.0,
                 width: int = 480, height: int = 360) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pts = ellipsoid_surface(CENTER, RADII)
    _, cams = orbit_rig(1, pitch, 1.0, (0.0, 0.0, 0.08), width, height, 65.0)
    from app.services.scanning.cameras import orbit_camera

    frames = []
    for i, yaw in enumerate(yaws):
        cam = orbit_camera(yaw, pitch, 1.0, (0.0, 0.0, 0.08), width, height, 65.0)
        mask = render_silhouette(cam, pts)
        img = _floor(floor, i, height, width)
        img[mask] = SKIN
        img = np.clip(img.astype(np.int16) + np.random.default_rng(i).integers(-6, 7, img.shape, dtype=np.int16), 0, 255).astype(np.uint8)
        path = out_dir / f"orbit_{i:02d}.jpg"
        cv2.imwrite(str(path), img)
        frames.append({"path": path, "yaw_deg": yaw, "pitch_deg": pitch})
    return frames


def full_ring(step: float = 15.0) -> list[float]:
    return [i * step for i in range(int(round(360 / step)))]


def ring_with_gap(gap_from: float, gap_to: float, step: float = 15.0) -> list[float]:
    """Every ``step`` degrees except the half-open range [gap_from, gap_to)."""
    return [y for y in full_ring(step) if not (gap_from <= y < gap_to)]


def topdown_with_paper(width_mm: float = FOOT_WIDTH_MM) -> np.ndarray:
    return paper_scene(foot_length_mm=FOOT_LENGTH_MM, foot_width_mm=width_mm)


def topdown_without_paper() -> np.ndarray:
    img = np.full((700, 900, 3), 120, np.uint8)
    cv2.ellipse(img, (450, 350), (200, 75), 10, 0, 360, SKIN, -1)
    return img
