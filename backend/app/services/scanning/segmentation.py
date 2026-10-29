"""Foot silhouette extraction for orbit frames.

Successor to the IA's ``ImageProcessor``: still a classical pipeline (threshold,
morphology, largest component) but with automatic polarity detection, a
saturation-based fallback for low-contrast floors and an optional GrabCut
refinement. A learned segmenter can be dropped in behind the same function
signature later.
"""
from __future__ import annotations

import cv2
import numpy as np

MAX_PROCESSING_SIDE = 720


def downscale_for_processing(image_bgr: np.ndarray, max_side: int = MAX_PROCESSING_SIDE) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    scale = max_side / float(max(h, w))
    if scale >= 1.0:
        return image_bgr
    return cv2.resize(image_bgr, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA)


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.uint8)
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(m)
    if contours:
        cv2.drawContours(out, contours, -1, 1, thickness=cv2.FILLED)
    return out.astype(bool)


def _largest_component_near_center(mask: np.ndarray) -> np.ndarray:
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if n <= 1:
        return np.zeros_like(mask, dtype=bool)
    h, w = mask.shape
    best, best_score = 0, -1.0
    for i in range(1, n):
        area = float(stats[i, cv2.CC_STAT_AREA])
        cx, cy = centroids[i]
        dist = float(np.hypot((cx - w / 2) / w, (cy - h / 2) / h))  # 0 (centre) .. ~0.7 (corner)
        score = area * max(0.1, 1.0 - 1.2 * dist)
        if score > best_score:
            best, best_score = i, score
    return labels == best


def _clean(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((5, 5), np.uint8)
    m = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel, iterations=2)
    comp = _largest_component_near_center(m > 0)
    return _fill_holes(comp)


def _otsu_mask(channel: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(channel, (7, 7), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = th > 0
    # The subject is centred and the frame border is background: flip polarity if needed.
    border = np.concatenate([mask[0, :], mask[-1, :], mask[:, 0], mask[:, -1]])
    if border.mean() > 0.5:
        mask = ~mask
    return mask


def _grabcut_mask(image_bgr: np.ndarray, center_fraction: float = 0.7, iterations: int = 3) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    small = downscale_for_processing(image_bgr, 480)
    sh, sw = small.shape[:2]
    rect = (
        int(sw * (1 - center_fraction) / 2),
        int(sh * (1 - center_fraction) / 2),
        int(sw * center_fraction),
        int(sh * center_fraction),
    )
    gc = np.zeros((sh, sw), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(small, gc, rect, bgd, fgd, iterations, cv2.GC_INIT_WITH_RECT)
    fg = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8)
    fg = cv2.resize(fg, (w, h), interpolation=cv2.INTER_NEAREST)
    return fg > 0


def silhouette_area_fraction(mask: np.ndarray) -> float:
    return float(mask.mean()) if mask.size else 0.0


def is_plausible(mask: np.ndarray, lo: float = 0.02, hi: float = 0.70) -> bool:
    frac = silhouette_area_fraction(mask)
    return lo <= frac <= hi


def segment(image_bgr: np.ndarray, method: str = "auto") -> tuple[np.ndarray, str]:
    """Return ``(mask, method_used)``; mask is boolean (True = foot) the same size as the image.

    ``method``: ``"otsu"`` (luminance), ``"saturation"``, ``"grabcut"`` or ``"auto"``, which tries
    them in that order until the result looks plausible. ``method_used`` is ``"none"`` when auto mode
    found no plausible silhouette at all. The quality checks use it: needing a fallback on many
    frames is a sign the floor is confusing the scan.
    """
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("empty image")
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    if method == "otsu":
        return _clean(_otsu_mask(gray)), "otsu"
    if method == "saturation":
        sat = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)[:, :, 1]
        return _clean(_otsu_mask(sat)), "saturation"
    if method == "grabcut":
        return _clean(_grabcut_mask(image_bgr)), "grabcut"
    if method != "auto":
        raise ValueError(f"unknown segmentation method: {method}")

    candidates = []
    for name in ("otsu", "saturation", "grabcut"):
        m, _ = segment(image_bgr, name)
        if is_plausible(m):
            return m, name
        candidates.append(m)
    # Nothing looked right: return the candidate closest to a typical foot area.
    return min(candidates, key=lambda c: abs(silhouette_area_fraction(c) - 0.2)), "none"


def extract_silhouette(image_bgr: np.ndarray, method: str = "auto") -> np.ndarray:
    """Mask only (see ``segment``)."""
    return segment(image_bgr, method)[0]
