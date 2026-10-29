"""TPU 'tub' footbed: a printed floor with a heel cup, side walls and a toe lip.

The tub is generated from the top-down paper measurement (scanning/scale.py):

1. Outline. The toe half of the foot comes from the measured contour. In a standing photo the
   lower leg covers the heel half, so the rear is modelled from the measured ball width with
   standard last proportions (heel about 62 % of ball width, waist about 75 %).
2. Allowance. Side room and toe room are added so the foot is not pinched.
3. Solid. The outline is offset outward by the wall thickness. Wall height varies along the
   foot (tall heel cup, lower sides, low toe lip). The floor carries an arch bump on the
   medial side. The mesh is built directly as a closed, watertight surface (no booleans).

Coordinates are millimetres: x runs heel (0) to toe, y across the foot, z up from the print bed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh


@dataclass
class TubParams:
    wall_thickness_mm: float = 2.5
    floor_thickness_mm: float = 3.0
    heel_cup_height_mm: float = 30.0
    side_wall_height_mm: float = 15.0
    toe_lip_height_mm: float = 8.0
    side_allowance_mm: float = 2.0
    toe_allowance_mm: float = 6.0
    arch_height_mm: float = 8.0
    # where the measured contour is trusted (fraction of length from the heel)
    measured_from: float = 0.50


@dataclass
class TubResult:
    mesh: trimesh.Trimesh
    inner_outline_mm: np.ndarray
    inner_length_mm: float
    inner_ball_width_mm: float
    medial_side: str
    params: TubParams = field(default_factory=TubParams)


# Rear-foot half-width as a fraction of half ball width, by fraction of length from the heel.
_REAR_PROFILE = np.array([
    [0.000, 0.00],
    [0.010, 0.30],
    [0.030, 0.47],
    [0.060, 0.57],
    [0.100, 0.61],
    [0.180, 0.63],
    [0.280, 0.66],
    [0.380, 0.73],
    [0.460, 0.84],
])


def _station_edges(contour: np.ndarray, x: float) -> tuple[float, float] | None:
    """Lowest and highest y where the closed contour crosses the line at length x."""
    ys = []
    n = len(contour)
    for i in range(n):
        (x0, y0), (x1, y1) = contour[i], contour[(i + 1) % n]
        if (x0 - x) * (x1 - x) <= 0 and x0 != x1:
            t = (x - x0) / (x1 - x0)
            ys.append(y0 + t * (y1 - y0))
    if len(ys) < 2:
        return None
    return min(ys), max(ys)


def foot_outline(contour_mm: np.ndarray, length_mm: float, ball_width_mm: float,
                 measured_from: float = 0.50, stations: int = 120) -> tuple[np.ndarray, str]:
    """Closed outline (N x 2, counter-clockwise), heel at x = 0, toe at x = length.

    ``contour_mm`` must already be in foot coordinates (x from heel to toe).
    Returns the outline and which side ('+y' or '-y') is medial (big-toe side).
    """
    c = np.asarray(contour_mm, dtype=float)
    xs = np.linspace(0.0, length_mm, stations)
    lo = np.full(stations, np.nan)
    hi = np.full(stations, np.nan)
    for i, x in enumerate(xs):
        if x >= measured_from * length_mm and x < length_mm:
            e = _station_edges(c, x)
            if e is not None:
                lo[i], hi[i] = e
    ok = ~np.isnan(lo)
    if ok.sum() < 5:
        raise ValueError("measured contour does not cover the toe half of the foot")
    first, last = int(np.argmax(ok)), int(len(ok) - 1 - np.argmax(ok[::-1]))
    # stop the stations at the last measured cross-section; the toe tip closes the outline
    xs, lo, hi, ok = xs[: last + 1], lo[: last + 1], hi[: last + 1], ok[: last + 1]
    # fill any interior gaps in the measured part
    idx = np.arange(len(xs))
    meas = idx >= first
    lo[meas] = np.interp(idx[meas], idx[ok], lo[ok])
    hi[meas] = np.interp(idx[meas], idx[ok], hi[ok])
    mid0 = 0.5 * (lo[first] + hi[first])
    # Rear: symmetric about the midline where the measurement starts, blended into the data.
    frac = xs / length_mm
    half_rear = np.interp(frac, _REAR_PROFILE[:, 0], _REAR_PROFILE[:, 1]) * ball_width_mm / 2
    blend = np.clip((idx - first) / 8.0, 0, 1)
    blend[~meas] = 0.0
    lo_f = np.where(meas, blend * lo + (1 - blend) * (mid0 - half_rear), mid0 - half_rear)
    hi_f = np.where(meas, blend * hi + (1 - blend) * (mid0 + half_rear), mid0 + half_rear)
    # Toe tip: the point of the measured contour furthest along x tells which toe is longest.
    tip = c[np.argmax(c[:, 0])]
    medial = "+y" if tip[1] > mid0 else "-y"
    # close the toe end with the measured tip so the outline is not cut square
    pts = np.concatenate([
        np.stack([xs, lo_f], axis=1),           # heel -> toe along the low-y edge
        tip[None, :],
        np.stack([xs, hi_f], axis=1)[::-1],     # toe -> heel along the high-y edge
    ])
    pts = pts - np.array([0.0, mid0])
    # drop duplicate heel points and degenerate stations
    keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 0.3:
            keep.append(i)
    pts = pts[keep]
    if np.linalg.norm(pts[0] - pts[-1]) < 0.3:
        pts = pts[:-1]
    if _signed_area(pts) < 0:
        pts = pts[::-1]
    return _resample_closed(pts, 240), medial


def _signed_area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _resample_closed(p: np.ndarray, n: int) -> np.ndarray:
    q = np.vstack([p, p[:1]])
    seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])], axis=1)


def _smooth_closed(p: np.ndarray, passes: int = 3) -> np.ndarray:
    for _ in range(passes):
        p = 0.25 * np.roll(p, 1, axis=0) + 0.5 * p + 0.25 * np.roll(p, -1, axis=0)
    return p


def _offset(p: np.ndarray, d: float) -> np.ndarray:
    """Offset a smooth counter-clockwise polygon outward by d along vertex normals."""
    t = np.roll(p, -1, axis=0) - np.roll(p, 1, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    normal = np.stack([t[:, 1], -t[:, 0]], axis=1)  # outward for CCW
    return p + d * normal


def apply_allowance(outline: np.ndarray, length_mm: float, params: TubParams) -> np.ndarray:
    p = outline.copy()
    # toe room: stretch the front half so the toe moves forward by toe_allowance
    front = p[:, 0] > 0.5 * length_mm
    p[front, 0] = 0.5 * length_mm + (p[front, 0] - 0.5 * length_mm) * (
        (0.5 * length_mm + params.toe_allowance_mm) / (0.5 * length_mm))
    return _smooth_closed(_offset(p, params.side_allowance_mm), 2)


def wall_height(frac: np.ndarray, p: TubParams) -> np.ndarray:
    """Wall top height above the bed along the foot (fraction of length from the heel)."""
    keys = np.array([0.0, 0.18, 0.35, 0.72, 0.86, 1.0])
    vals = np.array([p.heel_cup_height_mm, p.heel_cup_height_mm, p.side_wall_height_mm,
                     p.side_wall_height_mm, p.toe_lip_height_mm, p.toe_lip_height_mm])
    return np.interp(frac, keys, vals)


def floor_height(xy: np.ndarray, length: float, width: float, medial_sign: float,
                 p: TubParams) -> np.ndarray:
    """Top of the floor: flat plate plus a medial arch bump."""
    x, y = xy[:, 0], xy[:, 1]
    cx, cy = 0.40 * length, medial_sign * 0.22 * width
    sx, sy = 0.10 * length, 0.17 * width
    bump = p.arch_height_mm * np.exp(-0.5 * (((x - cx) / sx) ** 2 + ((y - cy) / sy) ** 2))
    return p.floor_thickness_mm + bump


def build_tub(contour_mm: np.ndarray, length_mm: float, ball_width_mm: float,
              params: TubParams | None = None, rings: int = 14) -> TubResult:
    p = params or TubParams()
    outline, medial = foot_outline(contour_mm, length_mm, ball_width_mm, p.measured_from)
    inner = apply_allowance(outline, length_mm, p)
    outer = _offset(inner, p.wall_thickness_mm)
    n = len(inner)
    L = float(inner[:, 0].max() - inner[:, 0].min())
    W = float(inner[:, 1].max() - inner[:, 1].min())
    x0 = inner[:, 0].min()
    frac = (inner[:, 0] - x0) / L
    h = wall_height(frac, p)
    msign = 1.0 if medial == "+y" else -1.0

    verts: list[np.ndarray] = []
    faces: list[list[int]] = []

    def add(v: np.ndarray) -> int:
        verts.append(v)
        return sum(len(a) for a in verts) - len(v)

    # Star-triangulated discs around the outline's centre (the outline is star-shaped about it).
    centre = np.array([inner[:, 0].mean(), 0.0])

    def disc(poly: np.ndarray, z_fn, flip: bool) -> int:
        """Concentric rings from the centre out to poly; returns index of the outermost ring."""
        ring_idx = []
        c = add(np.array([[centre[0], centre[1], float(z_fn(centre[None, :])[0])]]))
        for k in range(1, rings + 1):
            s = k / rings
            pts = centre + s * (poly - centre)
            ring_idx.append(add(np.column_stack([pts, z_fn(pts)])))
        m = len(poly)
        first = ring_idx[0]
        for i in range(m):
            tri = [c, first + i, first + (i + 1) % m]
            faces.append(tri[::-1] if flip else tri)
        for a, b in zip(ring_idx[:-1], ring_idx[1:]):
            for i in range(m):
                j = (i + 1) % m
                q1 = [a + i, b + i, b + j]
                q2 = [a + i, b + j, a + j]
                faces.extend([q1[::-1], q2[::-1]] if flip else [q1, q2])
        return ring_idx[-1]

    # bottom face (z = 0), facing down
    bottom = disc(outer, lambda q: np.zeros(len(q)), flip=True)
    # floor top over the inner outline, facing up
    floor_edge = disc(inner, lambda q: floor_height(q, L, W, msign, p), flip=False)
    floor_z = floor_height(inner, L, W, msign, p)
    h = np.maximum(h, floor_z + 2.0)
    outer_top = add(np.column_stack([outer, h]))
    inner_top = add(np.column_stack([inner, h]))

    for i in range(n):
        j = (i + 1) % n
        # outer wall: bottom outer ring -> outer top (faces outward)
        faces += [[bottom + i, bottom + j, outer_top + j], [bottom + i, outer_top + j, outer_top + i]]
        # rim: outer top -> inner top (faces up)
        faces += [[outer_top + i, outer_top + j, inner_top + j], [outer_top + i, inner_top + j, inner_top + i]]
        # inner wall: inner top -> floor edge (faces inward)
        faces += [[inner_top + i, inner_top + j, floor_edge + j], [inner_top + i, floor_edge + j, floor_edge + i]]

    mesh = trimesh.Trimesh(np.vstack(verts), np.array(faces), process=True)
    mesh.fix_normals()
    ball = float(np.ptp(inner[(frac > 0.6) & (frac < 0.8), 1])) if np.any((frac > 0.6) & (frac < 0.8)) else W
    return TubResult(mesh=mesh, inner_outline_mm=inner, inner_length_mm=L,
                     inner_ball_width_mm=ball, medial_side=medial, params=p)


def bed_fit(outline_mm: np.ndarray, bed_x: float, bed_y: float, step_deg: float = 1.0) -> float | None:
    """Smallest rotation (degrees) at which the outline fits a bed, or None if it never fits."""
    for a in np.arange(0, 90 + step_deg, step_deg):
        r = np.radians(a)
        rot = outline_mm @ np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]]).T
        span = np.ptp(rot, axis=0)
        if span[0] <= bed_x and span[1] <= bed_y:
            return float(a)
    return None
