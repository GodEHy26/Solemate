"""Photo -> Sole-Mate measurement -> printable TPU tub (STL), with preview images.

Usage (from the repo root):
    python scripts/make_tub.py path/to/photo.jpg [--paper A4] [--out tub_out]

The photo is a top-down shot of the foot on paper with the heel pressed against a stop
(a box or wall) touching one short edge of the paper. Writes tub.stl, outline.png, tub.png
and prints the dimensions and whether it fits common printer beds.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.services.insole.tub import TubParams, bed_fit, build_tub  # noqa: E402
from app.services.scanning.scale import (  # noqa: E402
    PAPER_SIZES_MM, _quad_aspect, detect_paper, measure_topdown, rectify, segment_foot_on_paper,
)


def foot_frame_contour(img, paper):
    """Contour in foot coordinates (x from heel at the paper edge to toe) plus length."""
    corners = detect_paper(img, paper)
    if corners is None:
        raise SystemExit("paper not found: shoot straight down with all four corners visible")
    short_mm, long_mm = PAPER_SIZES_MM[paper]
    aspect = _quad_aspect(corners)
    warped, mm_per_px = rectify(img, corners, paper)
    mask = segment_foot_on_paper(warped)
    td = measure_topdown(img, paper)
    if td is None:
        raise SystemExit("foot not found on the paper")
    h_mm = mask.shape[0] * mm_per_px
    ys = np.nonzero(mask)[0]
    heel_at_top = ys.min() <= 2  # mask touches the top edge -> heel against a stop there
    c = np.array(td.contour_mm, dtype=float)
    # x along the paper's long axis from the heel edge; y across
    if heel_at_top:
        x, y = c[:, 1], c[:, 0]
    else:
        x, y = h_mm - c[:, 1], -c[:, 0]
    # correct the small scale error the detected sheet shows on its long side
    k = (long_mm / short_mm) / aspect
    x = x * k
    contour = np.stack([x, y], axis=1)
    return contour, float(x.max()), td.width_mm, aspect


def plot_outline(contour, res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4, 8))
    shift = np.median(contour[contour[:, 0] > 0.5 * contour[:, 0].max(), 1]) - np.median(res.inner_outline_mm[res.inner_outline_mm[:, 0] > 0.5 * res.inner_length_mm, 1])
    ax.plot(contour[:, 1] - shift, contour[:, 0], color="#999", lw=1, label="Sole-Mate contour")
    o = np.vstack([res.inner_outline_mm, res.inner_outline_mm[:1]])
    ax.plot(o[:, 1], o[:, 0], color="#d33", lw=2, label="tub inner outline")
    ax.set_aspect("equal")
    ax.set_xlabel("width (mm)")
    ax.set_ylabel("heel -> toe (mm)")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower center", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def render(mesh, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    tris = mesh.vertices[mesh.faces]
    n = mesh.face_normals
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
    colors = np.column_stack([0.15 + 0.6 * shade, 0.15 + 0.6 * shade, 0.2 + 0.7 * shade, np.ones_like(shade)])
    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolor="none"))
    lo, hi = mesh.bounds
    span = (hi - lo).max()
    c = (hi + lo) / 2
    ax.set_xlim(c[0] - span / 2, c[0] + span / 2)
    ax.set_ylim(c[1] - span / 2, c[1] + span / 2)
    ax.set_zlim(0, span / 2)
    ax.set_box_aspect((1, 1, 0.5))
    ax.view_init(elev=28, azim=-60)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--paper", default="A4")
    ap.add_argument("--out", default="tub_out")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    img = cv2.imread(a.photo)
    if img is None:
        raise SystemExit(f"could not read {a.photo}")
    paper = a.paper.upper()
    contour, length, width, aspect = foot_frame_contour(img, paper)
    res = build_tub(contour, length, width, TubParams())
    m = res.mesh
    m.export(out / "tub.stl")
    plot_outline(contour, res, out / "outline.png")
    render(m, out / "tub.png")
    lo, hi = m.bounds
    size = hi - lo
    print(f"paper side ratio     {aspect:.3f}")
    print(f"foot length          {length:.1f} mm   forefoot width {width:.1f} mm (Sole-Mate)")
    print(f"tub inside           {res.inner_length_mm:.1f} x {res.inner_ball_width_mm:.1f} mm")
    print(f"tub outside          {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm")
    print(f"medial (arch) side   {res.medial_side}   watertight {m.is_watertight}   volume {m.volume / 1000:.1f} cm3")
    print(f"TPU estimate         {m.volume / 1000 * 1.21:.0f} g solid (less with infill)")
    for bx, by in [(220, 220), (256, 256), (300, 300)]:
        ang = bed_fit(np.asarray(m.vertices)[:, :2] - lo[:2], bx, by)
        print(f"fits {bx}x{by} bed      " + ("no" if ang is None else f"yes, rotated {ang:.0f} deg"))
    print(f"files                {out}/tub.stl, outline.png, tub.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
