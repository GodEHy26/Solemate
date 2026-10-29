






from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "LETTER": (215.9, 279.4),
    "A3": (297.0, 420.0),
}
RECTIFIED_PX_PER_MM = 3.0


@dataclass
class TopDownMeasurement:
    length_mm: float
    width_mm: float
    mm_per_px: float
    paper: str
    contour_mm: list[list[float]]
    angle_deg: float

    def to_dict(self) -> dict:
        return {
            "length_mm": round(self.length_mm, 1),
            "width_mm": round(self.width_mm, 1),
            "mm_per_px": round(self.mm_per_px, 4),
            "paper": self.paper,
            "angle_deg": round(self.angle_deg, 1),
            "contour_mm": self.contour_mm,
        }


def order_corners(pts: np.ndarray) -> np.ndarray:

    pts = np.asarray(pts, dtype=np.float64).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def _quad_aspect(quad: np.ndarray) -> float:
    tl, tr, br, bl = quad
    w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    return max(w, h) / max(min(w, h), 1e-6)


def _is_frame_border(quad: np.ndarray, shape: tuple[int, int], margin: int = 3) -> bool:

    h, w = shape
    near = [(x <= margin or x >= w - 1 - margin) and (y <= margin or y >= h - 1 - margin) for x, y in quad]
    return sum(near) >= 3


def detect_paper(
    image_bgr: np.ndarray,
    paper: str | None = None,
    min_area_fraction: float = 0.10,
    max_area_fraction: float = 0.92,
    aspect_tolerance: float = 0.20,
) -> np.ndarray | None:





    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    img_area = float(gray.shape[0] * gray.shape[1])
    for bright in _bright_masks(blur):
        quad = _find_paper_quad(bright, gray.shape, img_area, paper, min_area_fraction,
                                max_area_fraction, aspect_tolerance)
        if quad is not None:
            return quad
    return None


def _bright_masks(blur: np.ndarray):







    kernel = np.ones((9, 9), np.uint8)
    t1, first = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    yield cv2.morphologyEx(first, cv2.MORPH_CLOSE, kernel)
    upper = blur[blur > t1]
    if upper.size > 1000:
        t2, _ = cv2.threshold(upper.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield cv2.morphologyEx((blur > t2).astype(np.uint8) * 255, cv2.MORPH_CLOSE, kernel)


def _find_paper_quad(bright, shape, img_area, paper, min_area_fraction, max_area_fraction,
                     aspect_tolerance) -> np.ndarray | None:
    contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    expected = None
    if paper and paper.upper() in PAPER_SIZES_MM:
        a, b = PAPER_SIZES_MM[paper.upper()]
        expected = b / a
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        hull = cv2.convexHull(contour)
        area = cv2.contourArea(hull) / img_area
        if area < min_area_fraction or area > max_area_fraction:
            continue
        peri = cv2.arcLength(hull, True)
        for eps in (0.02, 0.03, 0.05):
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) != 4:
                continue
            quad = order_corners(approx.reshape(4, 2))
            if _is_frame_border(quad, shape):
                break
            if expected and abs(_quad_aspect(quad) - expected) / expected > aspect_tolerance:
                break
            return quad
    return None


def rectify(image_bgr: np.ndarray, corners: np.ndarray, paper: str = "A4") -> tuple[np.ndarray, float]:

    short_mm, long_mm = PAPER_SIZES_MM[paper.upper()]
    tl, tr, br, bl = corners
    top_len = np.linalg.norm(tr - tl)
    left_len = np.linalg.norm(bl - tl)
    if top_len >= left_len:
        w_mm, h_mm = long_mm, short_mm
    else:
        w_mm, h_mm = short_mm, long_mm
    w_px = int(round(w_mm * RECTIFIED_PX_PER_MM))
    h_px = int(round(h_mm * RECTIFIED_PX_PER_MM))
    dst = np.array([[0, 0], [w_px - 1, 0], [w_px - 1, h_px - 1], [0, h_px - 1]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(corners.astype(np.float32), dst)
    warped = cv2.warpPerspective(image_bgr, H, (w_px, h_px))
    return warped, 1.0 / RECTIFIED_PX_PER_MM


def segment_foot_on_paper(warped_bgr: np.ndarray, margin_fraction: float = 0.005) -> np.ndarray:

    gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = th.shape
    my, mx = int(h * margin_fraction), int(w * margin_fraction)
    th[:my, :] = 0
    th[-my:, :] = 0
    th[:, :mx] = 0
    th[:, -mx:] = 0
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
    if n <= 1:
        return np.zeros_like(th, dtype=bool)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return labels == largest


def _forefoot_width_px(mask: np.ndarray, station_px: float = 6.0) -> float | None:







    ys, xs = np.nonzero(mask)
    if len(xs) < 500:
        return None
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    centre = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - centre, full_matrices=False)
    axis, perp = vt[0], vt[1]
    u = (pts - centre) @ axis
    v = (pts - centre) @ perp
    edges = np.arange(u.min(), u.max() + station_px, station_px)
    idx = np.digitize(u, edges)
    widths = np.array([np.ptp(v[idx == i]) if np.any(idx == i) else 0.0 for i in range(1, len(edges))])
    if len(widths) < 10:
        return None
    h, w = mask.shape
    touching = (xs <= 1) | (xs >= w - 2) | (ys <= 1) | (ys >= h - 2)
    if touching.any():
        heel_at_low_u = u[touching].mean() < 0
    else:
        q = max(1, len(widths) // 5)
        heel_at_low_u = widths[:q].mean() > widths[-q:].mean()
    half = len(widths) // 2
    toe_half = widths[half:] if heel_at_low_u else widths[:half]
    return float(toe_half.max())


def measure_topdown(image_bgr: np.ndarray, paper: str = "A4") -> TopDownMeasurement | None:

    paper = paper.upper()
    if paper not in PAPER_SIZES_MM:
        raise ValueError(f"unknown paper size: {paper}")
    corners = detect_paper(image_bgr, paper)
    if corners is None:
        return None
    warped, mm_per_px = rectify(image_bgr, corners, paper)
    mask = segment_foot_on_paper(warped)
    if mask.sum() < 500:
        return None
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    (_cx, _cy), (rw, rh), angle = cv2.minAreaRect(contour)
    length_px, width_px = max(rw, rh), min(rw, rh)
    forefoot_width_px = _forefoot_width_px(mask)
    if forefoot_width_px is not None:
        width_px = min(width_px, forefoot_width_px)
    approx = cv2.approxPolyDP(contour, 1.5, True).reshape(-1, 2)
    contour_mm = [[round(float(x * mm_per_px), 1), round(float(y * mm_per_px), 1)] for x, y in approx]
    return TopDownMeasurement(
        length_mm=float(length_px * mm_per_px),
        width_mm=float(width_px * mm_per_px),
        mm_per_px=mm_per_px,
        paper=paper,
        contour_mm=contour_mm,
        angle_deg=float(angle),
    )
