






from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import trimesh

from ...config import Settings, get_settings
from .capture_plan import ORBIT_KIND, TOPDOWN_KIND, validate_coverage
from .cameras import orbit_camera
from .measurements import FootGeometry, aligned_mesh, analyze_foot
from .meshing import grid_to_mesh, load_mesh, mesh_to_grid
from .scale import measure_topdown
from .quality import FrameStat, ScanWarning, check_agreement, check_background, check_orbit, check_scale, confidence
from .segmentation import downscale_for_processing, is_plausible, segment
from .visual_hull import ReconstructionError, VoxelGrid, carve_adaptive

ANKLE_CUT_RATIO = 0.34


@dataclass
class FrameInput:
    path: Path
    kind: str
    yaw_deg: float
    pitch_deg: float
    index: int = 0


@dataclass
class ScanResult:
    mesh: trimesh.Trimesh
    grid: VoxelGrid
    geometry: FootGeometry
    source: str
    scale_method: str
    scale_confidence: str
    scale_factor: float
    frames_used: int
    topdown: dict | None = None
    warnings: list[ScanWarning] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    frame_stats: list[FrameStat] = field(default_factory=list)

    @property
    def confidence(self) -> str:
        return confidence(self.warnings)


class Reconstructor(Protocol):
    def reconstruct(self, *args, **kwargs) -> ScanResult: ...


def clip_height(grid: VoxelGrid, z_max: float) -> VoxelGrid:

    z = grid.origin[2] + np.arange(grid.shape[2]) * grid.spacing[2]
    keep = z <= z_max
    occ = grid.occupancy.copy()
    occ[:, :, ~keep] = False
    if not occ.any():
        raise ReconstructionError("ankle cut removed the whole volume")
    return VoxelGrid(occ, grid.origin.copy(), grid.spacing.copy())


class VisualHullReconstructor:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _views(self, frames: list[FrameInput], notes: list[str], stats: list[FrameStat]):
        masks, cams, yaws = [], [], []
        s = self.settings
        target = (0.0, 0.0, 0.08 * s.capture_radius_units)
        for f in frames:
            img = cv2.imread(str(f.path))
            if img is None:
                notes.append(f"frame {f.index}: unreadable image, skipped")
                stats.append(FrameStat(f.yaw_deg, "none", 0.0, False))
                continue
            img = downscale_for_processing(img)
            mask, method = segment(img, "auto")
            usable = method != "none" and is_plausible(mask)
            stats.append(FrameStat(f.yaw_deg, method, float(mask.mean()), usable))
            if not usable:
                notes.append(f"frame {f.index}: no plausible foot silhouette, skipped")
                continue
            h, w = mask.shape
            cams.append(orbit_camera(f.yaw_deg, f.pitch_deg, s.capture_radius_units, target, w, h, s.camera_hfov_deg))
            masks.append(mask)
            yaws.append(f.yaw_deg)
        return masks, cams, yaws

    def reconstruct(
        self,
        frames: list[FrameInput],
        known_length_mm: float | None = None,
        paper: str | None = None,
    ) -> ScanResult:
        s = self.settings
        notes: list[str] = []
        stats: list[FrameStat] = []
        orbit = [f for f in frames if f.kind == ORBIT_KIND]
        topdown = [f for f in frames if f.kind == TOPDOWN_KIND]
        if len(orbit) < s.min_orbit_frames:
            raise ReconstructionError(f"need at least {s.min_orbit_frames} orbit frames, got {len(orbit)}")

        masks, cams, yaws = self._views(orbit, notes, stats)
        background = check_background(stats)
        if len(masks) < s.min_orbit_frames:
            raise ReconstructionError(
                f"only {len(masks)} usable silhouettes (need {s.min_orbit_frames}); " + "; ".join(notes),
                warnings=background,
            )
        ok, problems = validate_coverage(yaws, s.sector_deg, min_fraction=0.5, max_gap_deg=120.0)
        if not ok:
            raise ReconstructionError(
                "insufficient angular coverage: " + " ".join(problems),
                warnings=background + check_orbit(yaws, s.sector_deg),
            )

        try:
            return self._build(frames, topdown, masks, cams, yaws, background, notes, stats, known_length_mm, paper)
        except ReconstructionError as exc:


            if not exc.warnings:
                exc.warnings = background + check_orbit(yaws, s.sector_deg)
            raise

    def _build(self, frames, topdown, masks, cams, yaws, background, notes, stats, known_length_mm, paper) -> ScanResult:
        s = self.settings
        r = s.capture_radius_units
        bounds = np.array([[-0.6 * r, 0.6 * r], [-0.6 * r, 0.6 * r], [0.0, 0.5 * r]])
        grid_units = carve_adaptive(masks, cams, bounds, s.coarse_resolution, s.voxel_resolution)
        unscaled = analyze_foot(grid_units, mesh=None, stations=40)
        length_units = unscaled.measurements.length_mm

        topdown_info = None
        if topdown:
            img = cv2.imread(str(topdown[0].path))
            td = measure_topdown(img, paper or s.paper_size) if img is not None else None
            if td is not None:
                topdown_info = td.to_dict()
            else:
                notes.append("top-down frame: paper sheet not detected; falling back to another scale source")

        if topdown_info is not None:
            scale, method, confidence = topdown_info["length_mm"] / length_units, "paper", "high"
        elif known_length_mm:

            scale, method, confidence = float(known_length_mm) / length_units, "known_length", "low"
        else:
            scale, method, confidence = s.default_capture_radius_mm / r, "assumed", "low"
            notes.append("No scale reference: measurements assume a 45 cm capture distance.")

        grid_mm = grid_units.scaled(scale)
        length_mm = length_units * scale
        grid_mm = clip_height(grid_mm, ANKLE_CUT_RATIO * length_mm)
        mesh = grid_to_mesh(grid_mm)
        geometry = analyze_foot(grid_mm, mesh)

        model_width = max((w["width_mm"] for w in geometry.width_profile), default=0.0)
        warnings = (
            check_scale(method)
            + check_orbit(yaws, s.sector_deg)
            + background
            + check_agreement(topdown_info["width_mm"] if topdown_info else None, model_width, float(grid_mm.spacing.mean()))
        )
        return ScanResult(
            mesh=aligned_mesh(mesh, grid_mm),
            grid=grid_mm,
            geometry=geometry,
            source="visual_hull",
            scale_method=method,
            scale_confidence=confidence,
            scale_factor=scale,
            frames_used=len(masks),
            topdown=topdown_info,
            warnings=warnings,
            notes=notes,
            frame_stats=stats,
        )


class UploadedMeshReconstructor:


    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def reconstruct(self, mesh_path: Path, units: str = "mm") -> ScanResult:
        mesh = load_mesh(mesh_path, units)
        if len(mesh.faces) == 0:
            raise ReconstructionError("mesh has no faces")
        extent = mesh.bounds[1] - mesh.bounds[0]
        if extent.max() < 100 or extent.max() > 600:
            raise ReconstructionError(
                f"mesh is {extent.max():.0f} mm long after unit conversion; expected a foot (100-600 mm). Check 'units'."
            )
        grid = mesh_to_grid(mesh, self.settings.voxel_resolution)
        geometry = analyze_foot(grid, mesh)
        return ScanResult(
            mesh=aligned_mesh(mesh, grid),
            grid=grid,
            geometry=geometry,
            source="uploaded_mesh",
            scale_method="sensor",
            scale_confidence="high",
            scale_factor=1.0,
            frames_used=0,
        )
