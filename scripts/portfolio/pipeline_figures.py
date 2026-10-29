








from __future__ import annotations

import argparse
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import cv2  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from app.services.scanning.cameras import orbit_camera  # noqa: E402
from app.services.scanning.measurements import aligned_mesh, analyze_foot  # noqa: E402
from app.services.scanning.meshing import grid_to_mesh, load_mesh, mesh_to_grid  # noqa: E402
from app.services.scanning.reconstructor import FrameInput, ReconstructionError, VisualHullReconstructor  # noqa: E402
from app.services.scanning.scale import detect_paper, measure_topdown, rectify  # noqa: E402
from app.services.scanning.segmentation import downscale_for_processing, segment  # noqa: E402
from app.services.scanning.visual_hull import carve, largest_component  # noqa: E402
from tests.synthetic_scenarios import (  # noqa: E402
    full_ring, orbit_frames, ring_with_gap, topdown_with_paper, topdown_without_paper,
)

INK, ACCENT, GOOD, WARN, BAD, MUTED = "#1b1f2a", "#1a8fe3", "#1f9d6b", "#d98a00", "#d64545", "#7a8294"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.titleweight": "bold", "figure.dpi": 150, "savefig.bbox": "tight"})


def save(fig, out: Path, name: str) -> None:
    fig.savefig(out / name, facecolor="white")
    plt.close(fig)
    print("saved", name)


def rgb(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)



def fig_silhouettes(frames, out, synthetic_note):
    picks = frames[:: max(1, len(frames) // 6)][:6]
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.4))
    for ax, f in zip(axes.ravel(), picks):
        img = downscale_for_processing(cv2.imread(str(f["path"])))
        mask, method = segment(img)
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        vis = img.copy()
        cv2.drawContours(vis, contours, -1, (60, 200, 90), 3)
        ax.imshow(rgb(vis))
        ax.set_title(f"yaw {f['yaw_deg']:.0f}°  ·  {method}", fontsize=9)
        ax.axis("off")
    fig.suptitle("1. Orbit frames → foot silhouettes (green)" + synthetic_note, fontweight="bold")
    save(fig, out, "fig-1-silhouettes.png")



def fig_paper(top_img, out, synthetic_note):
    corners = detect_paper(top_img, "A4")
    td = measure_topdown(top_img, "A4")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.6), gridspec_kw={"width_ratios": [1.3, 1]})
    vis = top_img.copy()
    if corners is not None:
        cv2.polylines(vis, [corners.astype(np.int32)], True, (227, 143, 26), 4)
    a.imshow(rgb(vis)); a.axis("off"); a.set_title("Top-down photo: sheet of A4 found (blue)")
    if corners is not None and td is not None:
        warped, mmpp = rectify(top_img, corners, "A4")
        b.imshow(rgb(warped), extent=[0, warped.shape[1] * mmpp, warped.shape[0] * mmpp, 0])
        c = np.array(td.contour_mm + td.contour_mm[:1])
        b.plot(c[:, 0], c[:, 1], color=GOOD, lw=2)
        b.set_xlabel("mm"); b.set_ylabel("mm")
        b.set_title(f"Rectified to millimetres: {td.length_mm:.0f} × {td.width_mm:.0f} mm")
    fig.suptitle("2. Real-world scale from a sheet of paper" + synthetic_note, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    save(fig, out, "fig-2-paper-scale.png")



def fig_hull(frames, out, synthetic_note):
    masks, cams = [], []
    for f in frames:
        img = downscale_for_processing(cv2.imread(str(f["path"])))
        m, _ = segment(img)
        h, w = m.shape
        masks.append(m)
        cams.append(orbit_camera(f["yaw_deg"], f["pitch_deg"], 1.0, (0, 0, 0.08), w, h, 65.0))
    bounds = np.array([[-0.6, 0.6], [-0.6, 0.6], [0.0, 0.5]])
    stages = [("2 views", 2), ("6 views", 6), (f"all {len(masks)} views", len(masks))]
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 5.6))
    for col, (label, n) in enumerate(stages):
        idx = np.linspace(0, len(masks) - 1, n).round().astype(int)
        grid = largest_component(carve([masks[i] for i in idx], [cams[i] for i in idx], bounds, 64))
        occ = grid.occupancy
        axes[0, col].imshow(occ.any(axis=2).T, origin="lower", cmap="Blues")
        axes[1, col].imshow(occ.any(axis=1).T, origin="lower", cmap="Blues")
        axes[0, col].set_title(f"{label}: {occ.sum():,} voxels left")
        for r in (0, 1):
            axes[r, col].set_xticks([]); axes[r, col].set_yticks([])
    axes[0, 0].set_ylabel("from above"); axes[1, 0].set_ylabel("from the side")
    fig.suptitle("3. Visual hull: each view carves away space the foot can't be in" + synthetic_note, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    save(fig, out, "fig-3-visual-hull.png")



def fig_mesh(mesh, out, note):
    v, f = mesh.vertices, mesh.faces
    fig = plt.figure(figsize=(12, 3.6))
    for i, (elev, azim, title) in enumerate([(25, -60, "three-quarter"), (0, -90, "side"), (90, -90, "top")]):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        tris = v[f]
        normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-9
        light = np.array([0.3, -0.4, 0.85]) / np.linalg.norm([0.3, -0.4, 0.85])
        shade = 0.40 + 0.60 * np.abs(normals @ light)
        colors = np.c_[0.86 * shade, 0.70 * shade, 0.55 * shade, np.ones_like(shade)]
        ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolor="none", antialiased=False))
        lo, hi = v.min(axis=0), v.max(axis=0)
        pad = 0.04 * (hi - lo)
        lo, hi = lo - pad, hi + pad
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
        ax.set_box_aspect(hi - lo, zoom=0.95)
        ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); ax.set_title(title)
    fig.suptitle(f"4. Watertight mesh ({len(mesh.faces):,} triangles), exported as GLB/OBJ" + note, fontweight="bold")
    fig.subplots_adjust(top=0.8, wspace=0.02)
    save(fig, out, "fig-4-mesh.png")



def fig_measurements(geo, out, note):
    m = geo.measurements
    fig = plt.figure(figsize=(11, 6.4))
    ax = fig.add_subplot(2, 2, (1, 2))
    poly = np.array(geo.footprint_mm + geo.footprint_mm[:1])
    ax.fill(poly[:, 0], poly[:, 1], color=ACCENT, alpha=0.15)
    ax.plot(poly[:, 0], poly[:, 1], color=ACCENT, lw=2)
    top = poly[:, 1].max()
    for i, (x, label) in enumerate(((0.1 * m.length_mm, f"heel {m.heel_width_mm:.0f} mm"),
                                    (m.waist_position_mm, f"waist {m.waist_width_mm:.0f} mm"),
                                    (m.ball_position_mm, f"ball {m.ball_width_mm:.0f} mm"))):
        ax.axvline(x, color=MUTED, ls="--", lw=1)
        ax.text(x + 2, top + 5 + 9 * (i % 2), label, fontsize=9, color=INK)
    ax.set_aspect("equal"); ax.set_xlabel("heel → toe (mm)"); ax.set_ylabel("mm")
    ax.set_title(f"Footprint contour · length {m.length_mm:.0f} mm")
    ax.set_ylim(poly[:, 1].min() - 10, top + 26)

    wp = geo.width_profile; hp = geo.height_profile
    a2 = fig.add_subplot(2, 2, 3)
    a2.plot([p["pct"] for p in wp], [p["width_mm"] for p in wp], color=ACCENT, lw=2)
    for lo, hi, c, lbl in ((0, 20, MUTED, "heel"), (35, 55, WARN, "waist"), (55, 80, GOOD, "ball"), (85, 100, MUTED, "toe")):
        a2.axvspan(lo, hi, color=c, alpha=0.10)
        a2.text((lo + hi) / 2, 0.04, lbl, ha="center", fontsize=8, color=c, transform=a2.get_xaxis_transform())
    a2.set_xlabel("% of foot length"); a2.set_ylabel("width (mm)"); a2.set_title("Width profile with landmark windows")
    a3 = fig.add_subplot(2, 2, 4)
    for s, c in zip(geo.sections, (GOOD, WARN, ACCENT)):
        p = np.array(s["points"] + s["points"][:1])
        a3.plot(p[:, 0], p[:, 1], color=c, lw=2, label=f"{s['name']} girth {s['girth_mm']:.0f} mm" if s["girth_mm"] else s["name"])
    a3.set_aspect("equal"); a3.legend(fontsize=8, loc="upper right"); a3.set_xlabel("mm"); a3.set_ylabel("height (mm)")
    a3.set_title("Cross-sections → girths")
    fig.suptitle("5. Measurements for the custom last" + note, fontweight="bold")
    fig.tight_layout()
    save(fig, out, "fig-5-measurements.png")



def fig_quality(out):
    cases = [
        ("Clean scan", full_ring(), "plain", "paper"),
        ("Heel side missed", ring_with_gap(150, 240), "plain", "paper"),
        ("No sheet of paper", full_ring(), "plain", "none"),
        ("Tiled rug", full_ring(), "tiles", "paper"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(14, 5.2))
    for ax, (title, yaws, floor, top) in zip(axes, cases):
        tmp = Path(tempfile.mkdtemp())
        fr = orbit_frames(tmp, yaws, floor)
        frames = [FrameInput(f["path"], "orbit", f["yaw_deg"], f["pitch_deg"], i + 1) for i, f in enumerate(fr)]
        p = tmp / "top.jpg"
        cv2.imwrite(str(p), topdown_with_paper() if top == "paper" else topdown_without_paper())
        frames.insert(0, FrameInput(p, "topdown", 0, 90, 0))
        try:
            r = VisualHullReconstructor().reconstruct(frames)
            warnings, conf = r.warnings, r.confidence
        except ReconstructionError as e:
            warnings, conf = e.warnings, "failed"
        sample = cv2.imread(str(fr[len(fr) // 3]["path"]))
        ax.imshow(rgb(sample)); ax.axis("off")
        color = {"high": GOOD, "medium": WARN, "low": BAD}.get(conf, BAD)
        ax.set_title(f"{title}\nconfidence: {conf}", color=color)
        lines = []
        for w in warnings:
            tag = "BLOCKS SIZE" if w.severity == "block" else "WARNING"
            lines += textwrap.wrap(f"{tag}: {w.message}", 44, subsequent_indent="  ")
            lines += textwrap.wrap(f"Fix: {w.fix}", 40, initial_indent="  ", subsequent_indent="  ")
        text = "\n".join(lines) or "No warnings: one size shown"
        ax.text(0, -0.04, text, transform=ax.transAxes, va="top", fontsize=8, wrap=True, color=INK)
        print(f"  {title}: {conf} {[w.code for w in warnings]}")
    fig.suptitle("6. Automatic scan-quality checks (synthetic test scans)", fontweight="bold")
    fig.subplots_adjust(wspace=0.12, bottom=0.3)
    save(fig, out, "fig-6-quality-checks.png")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mesh", help="GLB/OBJ of your own foot (download it from the foot profile page)")
    ap.add_argument("--out", default=str(ROOT / "portfolio-shots"))
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    syn = "\n(synthetic test foot)"

    tmp = Path(tempfile.mkdtemp())
    frames = orbit_frames(tmp / "orbit", full_ring())
    fig_silhouettes(frames, out, syn)
    fig_paper(topdown_with_paper(), out, syn)
    fig_hull(frames, out, syn)

    if args.mesh:
        mesh = load_mesh(args.mesh, "mm")
        grid = mesh_to_grid(mesh, 128)
        note = "\n(my own foot scan)"
    else:
        all_frames = [FrameInput(f["path"], "orbit", f["yaw_deg"], f["pitch_deg"], i + 1) for i, f in enumerate(frames)]
        p = tmp / "top.jpg"; cv2.imwrite(str(p), topdown_with_paper())
        r = VisualHullReconstructor().reconstruct([FrameInput(p, "topdown", 0, 90, 0)] + all_frames)
        grid, mesh, note = r.grid, grid_to_mesh(r.grid), syn
    geo = analyze_foot(grid, mesh)
    fig_mesh(aligned_mesh(mesh, grid), out, note)
    fig_measurements(geo, out, note)
    fig_quality(out)
    print(f"\nDone. Figures are in {out}")


if __name__ == "__main__":
    main()
