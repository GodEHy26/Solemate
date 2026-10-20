"""Absolute scale from a sheet of paper in the top-down frame.

Silhouettes alone recover shape only up to scale. The top-down capture asks
the user to stand on a sheet of A4/Letter paper: the sheet's corners give a
homography to a metric plane, so foot length and width in millimetres can be
measured directly, and the 3D hull is scaled to match.
"""
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
    """Order 4 points as top-left, top-right, bottom-right, bottom-left."""
    pts = np.asarray(pts, dtype=np.float64).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def detect_paper(image_bgr: np.ndarray, min_area_fraction: float = 0.10) -> np.ndarray | None:
    """Find the bright paper sheet and return its 4 ordered corners in pixels, or None."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    _, bright = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    img_area = float(gray.shape[0] * gray.shape[1])
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        hull = cv2.convexHull(contour)  # repairs bites where the leg crosses the paper edge
        if cv2.contourArea(hull) < min_area_fraction * img_area:
            continue
        peri = cv2.arcLength(hull, True)
        for eps in (0.02, 0.03, 0.05):
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) == 4:
                return order_corners(approx.reshape(4, 2))
    return None


def rectify(image_bgr: np.ndarray, corners: np.ndarray, paper: str = "A4") -> tuple[np.ndarray, float]:
    """Warp the paper to a metric canvas; returns (warped image, mm per pixel)."""
    short_mm, long_mm = PAPER_SIZES_MM[paper.upper()]
    tl, tr, br, bl = corners
    top_len = np.linalg.norm(tr - tl)
    left_len = np.linalg.norm(bl - tl)
    if top_len >= left_len:  # landscape in the image
        w_mm, h_mm = long_mm, short_mm
    else:
        w_mm, h_mm = short_mm, long_mm
    w_px = int(round(w_mm * RECTIFIED_PX_PER_MM))
    h_px = int(round(h_mm * RECTIFIED_PX_PER_MM))
    dst = np.array([[0, 0], [w_px - 1, 0], [w_px - 1, h_px - 1], [0, h_px - 1]], dtype=np.float32)
    H = cv2.getPerspectiveTransform(corners.astype(np.float32), dst)
    warped = cv2.warpPerspective(image_bgr, H, (w_px, h_px))
    return warped, 1.0 / RECTIFIED_PX_PER_MM


def segment_foot_on_paper(warped_bgr: np.ndarray, margin_fraction: float = 0.02) -> np.ndarray:
    """Foot = darker/saturated region inside the rectified white sheet."""
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


def measure_topdown(image_bgr: np.ndarray, paper: str = "A4") -> TopDownMeasurement | None:
    """Metric foot length/width from a top-down photo of a foot on paper."""
    paper = paper.upper()
    if paper not in PAPER_SIZES_MM:
        raise ValueError(f"unknown paper size: {paper}")
    corners = detect_paper(image_bgr)
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
