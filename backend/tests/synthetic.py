






from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.services.scanning.cameras import Camera, orbit_camera


def ellipsoid_surface(center, radii, n: int = 6000) -> np.ndarray:

    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5**0.5) * i
    unit = np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], axis=1)
    return np.asarray(center) + unit * np.asarray(radii)


def render_silhouette(cam: Camera, surface_points: np.ndarray) -> np.ndarray:
    uv, depth = cam.project(surface_points)
    ok = depth > 0
    pts = np.rint(uv[ok]).astype(np.int32)
    mask = np.zeros((cam.height, cam.width), np.uint8)
    if len(pts) >= 3:
        hull = cv2.convexHull(pts)
        cv2.fillConvexPoly(mask, hull, 1)
    return mask.astype(bool)


def orbit_rig(n_views: int, pitch_deg: float, radius: float, target, width: int, height: int, hfov: float):
    yaws = [i * 360.0 / n_views for i in range(n_views)]
    cams = [orbit_camera(y, pitch_deg, radius, target, width, height, hfov) for y in yaws]
    return yaws, cams


def write_orbit_frames(
    out_dir: Path,
    surface_points: np.ndarray,
    n_views: int = 16,
    pitch_deg: float = 30.0,
    radius: float = 1.0,
    target=(0.0, 0.0, 0.08),
    width: int = 480,
    height: int = 360,
    hfov: float = 65.0,
) -> list[dict]:

    out_dir.mkdir(parents=True, exist_ok=True)
    yaws, cams = orbit_rig(n_views, pitch_deg, radius, target, width, height, hfov)
    frames = []
    for i, (yaw, cam) in enumerate(zip(yaws, cams)):
        mask = render_silhouette(cam, surface_points)
        img = np.full((height, width, 3), 225, np.uint8)
        img[mask] = (70, 60, 55)
        noise = np.random.default_rng(i).integers(-6, 7, img.shape, dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        path = out_dir / f"orbit_{i:02d}.jpg"
        cv2.imwrite(str(path), img)
        frames.append({"path": path, "yaw_deg": yaw, "pitch_deg": pitch_deg, "kind": "orbit", "index": i + 1})
    return frames


def paper_scene(
    foot_length_mm: float = 260.0,
    foot_width_mm: float = 96.0,
    paper: str = "A4",
    size=(900, 700),
    rotation_deg: float = 12.0,
) -> np.ndarray:

    from app.services.scanning.scale import PAPER_SIZES_MM

    w, h = size
    short_mm, long_mm = PAPER_SIZES_MM[paper]
    img = np.full((h, w, 3), 75, np.uint8)

    px_per_mm = 1.6
    cx, cy = w / 2, h / 2
    theta = np.radians(rotation_deg)
    R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])

    def to_img(pts_mm):
        pts = (np.asarray(pts_mm) - np.array([short_mm / 2, long_mm / 2])) * px_per_mm
        return pts @ R.T + np.array([cx, cy])

    corners_mm = [[0, 0], [short_mm, 0], [short_mm, long_mm], [0, long_mm]]
    cv2.fillConvexPoly(img, np.rint(to_img(corners_mm)).astype(np.int32), (245, 245, 245))
    t = np.linspace(0, 2 * np.pi, 400)
    ellipse_mm = np.stack(
        [short_mm / 2 + foot_width_mm / 2 * np.cos(t), long_mm / 2 + foot_length_mm / 2 * np.sin(t)], axis=1
    )
    cv2.fillPoly(img, [np.rint(to_img(ellipse_mm)).astype(np.int32)], (60, 70, 90))
    return img
