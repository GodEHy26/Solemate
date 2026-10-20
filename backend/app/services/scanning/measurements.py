"""Foot measurements from a reconstructed volume and mesh.

All inputs are in millimetres. The foot is first aligned so that its long
axis runs along +X with the heel at x = 0, the floor at z = 0 and the
footprint centred on y = 0; every landmark is then a window along X.

Landmark windows (fraction of foot length from the heel) follow common
last-making practice: heel 0-20 %, waist (narrowest) 35-55 %, instep 40-55 %,
ball (widest) 55-80 %, toes 85-100 %.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import atan2, cos, degrees, radians, sin

import cv2
import numpy as np
import trimesh

from .visual_hull import ReconstructionError, VoxelGrid

WINDOWS = {
    "heel": (0.00, 0.20),
    "waist": (0.35, 0.55),
    "instep": (0.40, 0.55),
    "ball": (0.55, 0.80),
    "toe": (0.85, 1.00),
}


@dataclass
class FootMeasurements:
    length_mm: float
    ball_width_mm: float
    heel_width_mm: float
    waist_width_mm: float
    toe_width_mm: float
    instep_height_mm: float
    ball_height_mm: float
    toe_height_mm: float
    ball_girth_mm: float | None
    waist_girth_mm: float | None
    instep_girth_mm: float | None
    ball_position_mm: float
    waist_position_mm: float
    instep_position_mm: float
    volume_cm3: float

    def as_dict(self) -> dict:
        return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in asdict(self).items()}

    def last_vector(self) -> tuple[float, float, float, float, float]:
        """5-D vector compatible with the reference-last KD-tree."""
        return (
            self.length_mm,
            self.ball_width_mm,
            self.toe_width_mm,
            self.toe_height_mm,
            self.waist_position_mm,
        )


@dataclass
class FootGeometry:
    measurements: FootMeasurements
    footprint_mm: list[list[float]]
    width_profile: list[dict] = field(default_factory=list)
    height_profile: list[dict] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    transform: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------
def _rot_z(theta: float) -> np.ndarray:
    c, s = cos(theta), sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _max_width(xy: np.ndarray, spacing: float, bins: int = 20) -> float:
    if len(xy) == 0:
        return 0.0
    edges = np.linspace(xy[:, 0].min(), xy[:, 0].max() + 1e-9, bins + 1)
    best = 0.0
    for i in range(bins):
        sel = (xy[:, 0] >= edges[i]) & (xy[:, 0] < edges[i + 1])
        if sel.any():
            best = max(best, float(xy[sel, 1].max() - xy[sel, 1].min()) + spacing)
    return best


def align_points(points: np.ndarray, spacing: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (R, offset) such that ``p_aligned = R @ p + offset`` puts the foot in canonical pose."""
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) < 10:
        raise ReconstructionError("too few points to align")
    xy = pts[:, :2]
    mean = xy.mean(axis=0)
    cov = np.cov((xy - mean).T)
    eigval, eigvec = np.linalg.eigh(cov)
    axis = eigvec[:, int(np.argmax(eigval))]
    theta = atan2(axis[1], axis[0])
    R = _rot_z(-theta)
    centered = pts - np.array([mean[0], mean[1], 0.0])
    aligned = centered @ R.T

    # Toe end is the wider end (ball vs heel): flip if the rear half is wider.
    mid = (aligned[:, 0].min() + aligned[:, 0].max()) / 2
    front = aligned[aligned[:, 0] >= mid]
    back = aligned[aligned[:, 0] < mid]
    if _max_width(back[:, :2], spacing) > _max_width(front[:, :2], spacing):
        flip = _rot_z(radians(180.0))
        R = flip @ R
        aligned = aligned @ flip.T

    offset_after = np.array(
        [
            -aligned[:, 0].min() + spacing / 2,          # heel face at x = 0
            -(aligned[:, 1].max() + aligned[:, 1].min()) / 2,  # centre footprint on y = 0
            -aligned[:, 2].min() + spacing / 2,          # floor at z = 0
        ]
    )
    total_offset = R @ (-np.array([mean[0], mean[1], 0.0])) + offset_after
    return R, total_offset


def transform_matrix(R: np.ndarray, offset: np.ndarray) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = offset
    return T


# ---------------------------------------------------------------------------
# Profiles and landmarks
# ---------------------------------------------------------------------------
def _profiles(pts: np.ndarray, spacing: float, bins: int = 60) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-station x centre, width and height along the foot."""
    length = pts[:, 0].max() + spacing / 2
    edges = np.linspace(0.0, length, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    widths = np.zeros(bins)
    heights = np.zeros(bins)
    for i in range(bins):
        sel = (pts[:, 0] >= edges[i]) & (pts[:, 0] < edges[i + 1])
        if sel.any():
            widths[i] = pts[sel, 1].max() - pts[sel, 1].min() + spacing
            heights[i] = pts[sel, 2].max() + spacing / 2
    return centers, widths, heights


def _window(centers: np.ndarray, length: float, name: str) -> np.ndarray:
    lo, hi = WINDOWS[name]
    sel = (centers >= lo * length) & (centers <= hi * length)
    if not sel.any():  # very coarse grid: fall back to nearest station
        idx = int(np.clip(np.argmin(np.abs(centers - (lo + hi) / 2 * length)), 0, len(centers) - 1))
        sel = np.zeros_like(centers, dtype=bool)
        sel[idx] = True
    return sel


def _girth(mesh: trimesh.Trimesh, x_mm: float) -> tuple[float | None, list[list[float]]]:
    """Perimeter of the mesh cross-section at x = x_mm and an ordered outline in (y, z)."""
    try:
        section = mesh.section(plane_origin=[x_mm, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
    except Exception:  # noqa: BLE001 - trimesh raises assorted errors on degenerate sections
        section = None
    if section is None:
        return None, []
    best_len, best_pts = 0.0, None
    for poly in section.discrete:
        poly = np.asarray(poly)
        if len(poly) < 3:
            continue
        seg = np.diff(np.vstack([poly, poly[:1]]), axis=0)
        length = float(np.linalg.norm(seg, axis=1).sum())
        if length > best_len:
            best_len, best_pts = length, poly
    if best_pts is None:
        return None, []
    step = max(1, len(best_pts) // 120)
    outline = [[round(float(p[1]), 2), round(float(p[2]), 2)] for p in best_pts[::step]]
    return best_len, outline


def _footprint_polygon(pts: np.ndarray, spacing: float) -> list[list[float]]:
    """Outline of the footprint (projection on the floor) as a polygon in mm."""
    x = pts[:, 0]
    y = pts[:, 1]
    ymin = y.min() - spacing
    nx = int(np.ceil((x.max() + spacing) / spacing)) + 2
    ny = int(np.ceil((y.max() - ymin + spacing) / spacing)) + 2
    mask = np.zeros((nx, ny), np.uint8)
    ix = np.clip(np.floor(x / spacing).astype(int), 0, nx - 1)
    iy = np.clip(np.floor((y - ymin) / spacing).astype(int), 0, ny - 1)
    mask[ix, iy] = 1
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))  # outline through voxel faces, not centres
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea)
    approx = cv2.approxPolyDP(contour, max(0.6, spacing * 0.5), True).reshape(-1, 2)
    # contour points are (col=iy, row=ix)
    poly = [[round(float(row * spacing), 2), round(float(ymin + col * spacing), 2)] for col, row in approx]
    return poly


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def analyze_foot(grid: VoxelGrid, mesh: trimesh.Trimesh | None = None, stations: int = 60) -> FootGeometry:
    """Compute measurements from a grid in millimetres (and optionally its mesh)."""
    spacing = float(np.mean(grid.spacing))
    raw = grid.occupied_points()
    if len(raw) == 0:
        raise ReconstructionError("empty volume")
    R, offset = align_points(raw, spacing)
    pts = raw @ R.T + offset

    length = float(pts[:, 0].max() + spacing / 2)
    centers, widths, heights = _profiles(pts, spacing, stations)

    def pick(name: str, arr: np.ndarray, fn) -> tuple[float, float]:
        sel = _window(centers, length, name)
        idx_local = fn(arr[sel])
        idx = int(np.flatnonzero(sel)[idx_local])
        return float(arr[idx]), float(centers[idx])

    ball_w, ball_x = pick("ball", widths, np.argmax)
    heel_w, _ = pick("heel", widths, np.argmax)
    waist_w, waist_x = pick("waist", widths, np.argmin)
    toe_w, _ = pick("toe", widths, np.argmax)
    instep_h, instep_x = pick("instep", heights, np.argmax)
    toe_h, _ = pick("toe", heights, np.argmax)
    ball_h = float(heights[int(np.argmin(np.abs(centers - ball_x)))])

    aligned_mesh = None
    if mesh is not None and len(mesh.faces) > 0:
        aligned_mesh = mesh.copy()
        aligned_mesh.apply_transform(transform_matrix(R, offset))

    sections: list[dict] = []
    girths: dict[str, float | None] = {"ball": None, "waist": None, "instep": None}
    if aligned_mesh is not None:
        for name, x_mm in (("ball", ball_x), ("waist", waist_x), ("instep", instep_x)):
            g, outline = _girth(aligned_mesh, x_mm)
            girths[name] = g
            sections.append(
                {
                    "name": name,
                    "x_mm": round(x_mm, 1),
                    "pct": round(100.0 * x_mm / length, 1),
                    "girth_mm": round(g, 1) if g else None,
                    "points": outline,
                }
            )

    measurements = FootMeasurements(
        length_mm=length,
        ball_width_mm=ball_w,
        heel_width_mm=heel_w,
        waist_width_mm=waist_w,
        toe_width_mm=toe_w,
        instep_height_mm=instep_h,
        ball_height_mm=ball_h,
        toe_height_mm=toe_h,
        ball_girth_mm=girths["ball"],
        waist_girth_mm=girths["waist"],
        instep_girth_mm=girths["instep"],
        ball_position_mm=ball_x,
        waist_position_mm=waist_x,
        instep_position_mm=instep_x,
        volume_cm3=grid.volume() / 1000.0,
    )

    width_profile = [
        {"pct": round(100 * c / length, 1), "x_mm": round(float(c), 1), "width_mm": round(float(w), 1)}
        for c, w in zip(centers, widths)
    ]
    height_profile = [
        {"pct": round(100 * c / length, 1), "x_mm": round(float(c), 1), "height_mm": round(float(h), 1)}
        for c, h in zip(centers, heights)
    ]
    rotation_deg = degrees(atan2(R[1, 0], R[0, 0]))
    return FootGeometry(
        measurements=measurements,
        footprint_mm=_footprint_polygon(pts, spacing),
        width_profile=width_profile,
        height_profile=height_profile,
        sections=sections,
        transform={"rotation_z_deg": round(rotation_deg, 2), "offset_mm": [round(float(v), 2) for v in offset]},
    )


def aligned_mesh(mesh: trimesh.Trimesh, grid: VoxelGrid) -> trimesh.Trimesh:
    """Return a copy of ``mesh`` in the canonical foot pose used by ``analyze_foot``."""
    spacing = float(np.mean(grid.spacing))
    R, offset = align_points(grid.occupied_points(), spacing)
    out = mesh.copy()
    out.apply_transform(transform_matrix(R, offset))
    return out
