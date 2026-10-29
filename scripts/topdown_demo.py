"""Run Sole-Mate's top-down paper measurement on one photo and save every stage as an image.

Usage (from the repo root):
    python scripts/topdown_demo.py path/to/photo.jpg [--paper A4] [--out demo_out]

Writes 1_input.jpg, 2_paper_detected.jpg, 3_rectified.jpg, 4_foot_mask.jpg, 5_result.jpg and
contour_mm.csv to the output folder, and prints the measurements.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.scanning.scale import (  # noqa: E402
    _quad_aspect, detect_paper, measure_topdown, rectify, segment_foot_on_paper, PAPER_SIZES_MM,
)


def label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    s = max(0.6, out.shape[1] / 1200)
    cv2.rectangle(out, (0, 0), (out.shape[1], int(44 * s)), (20, 20, 20), -1)
    cv2.putText(out, text, (10, int(32 * s)), cv2.FONT_HERSHEY_SIMPLEX, s, (255, 255, 255), 2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--paper", default="A4")
    ap.add_argument("--out", default="demo_out")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(a.photo)
    if img is None:
        print(f"could not read {a.photo}")
        return 1
    cv2.imwrite(str(out / "1_input.jpg"), label(img, "1. Input photo"))

    corners = detect_paper(img, a.paper)
    if corners is None:
        print("paper not found: shoot straight down with all four corners visible")
        return 2
    short_mm, long_mm = PAPER_SIZES_MM[a.paper.upper()]
    aspect = _quad_aspect(corners)
    det = img.copy()
    cv2.polylines(det, [corners.astype(int)], True, (0, 255, 0), 8)
    for x, y in corners.astype(int):
        cv2.circle(det, (x, y), 18, (0, 0, 255), -1)
    cv2.imwrite(str(out / "2_paper_detected.jpg"),
                label(det, f"2. Paper found: side ratio {aspect:.3f} (A4 = {long_mm / short_mm:.3f})"))

    warped, mm_per_px = rectify(img, corners, a.paper)
    grid = warped.copy()
    step = int(round(10 / mm_per_px))
    for k in range(0, grid.shape[0], step):
        cv2.line(grid, (0, k), (grid.shape[1], k), (255, 160, 0), 1)
    for k in range(0, grid.shape[1], step):
        cv2.line(grid, (k, 0), (k, grid.shape[0]), (255, 160, 0), 1)
    cv2.imwrite(str(out / "3_rectified.jpg"), label(grid, "3. Flattened to mm (10 mm grid)"))

    mask = segment_foot_on_paper(warped)
    over = warped.copy()
    over[mask] = (0.45 * over[mask] + np.array([0, 0, 140])).astype(np.uint8)
    cv2.imwrite(str(out / "4_foot_mask.jpg"), label(over, "4. Foot segmented"))

    td = measure_topdown(img, a.paper)
    if td is None:
        print("foot not found on the paper")
        return 3
    res = warped.copy()
    pts = (np.array(td.contour_mm) / mm_per_px).astype(np.int32)
    cv2.polylines(res, [pts], True, (0, 0, 255), 3)
    cv2.imwrite(str(out / "5_result.jpg"),
                label(res, f"5. Length {td.length_mm:.1f} mm  Width {td.width_mm:.1f} mm"))
    with open(out / "contour_mm.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x_mm", "y_mm"])
        w.writerows(td.contour_mm)

    print(f"paper side ratio  {aspect:.3f}  (A4 = {long_mm / short_mm:.3f})")
    print(f"foot length       {td.length_mm:.1f} mm")
    print(f"forefoot width    {td.width_mm:.1f} mm")
    print(f"outline points    {len(td.contour_mm)}  -> {out / 'contour_mm.csv'}")
    print(f"stage images      {out}/1_input.jpg ... 5_result.jpg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
