"""Reconstruction strategies that turn captured input into a measured foot.

``VisualHullReconstructor`` is the browser path (photos only).
``UploadedMeshReconstructor`` accepts a mesh produced by a depth sensor
(ARKit / ARCore / LiDAR companion app) so both paths end in the same
``ScanResult`` and share measurements, sizing and last matching.
"""
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
from .segmentation import downscale_for_processing, extract_silhouette, is_plausible
from .visual_hull import ReconstructionError, VoxelGrid, carve_adaptive

ANKLE_CUT_RATIO = 0.34  # keep the hull below ~34 % of foot length (just above the ankle bones)


@dataclass
class FrameInput:
    path: Path
    kind: str
    yaw_deg: float
    pitch_deg: float
    index: int = 0


@dataclass
class ScanResult:
    mesh: trimesh.Trimesh          # canonical pose, millimetres
    grid: VoxelGrid                # millimetres, raw orientation
    geometry: FootGeometry
    source: str                    # visual_hull | uploaded_mesh
    scale_method: str              # paper | known_length | assumed | sensor
    scale_confidence: str          # high | medium | low
    scale_factor: float
    frames_used: int
    topdown: dict | None = None
    warnings: list[str] = field(default_factory=list)


class Reconstructor(Protocol):
    def reconstruct(self, *args, **kwargs) -> ScanResult: ...


def clip_height(grid: VoxelGrid, z_max: float) -> VoxelGrid:
    """Drop voxels above ``z_max`` (world units of the grid)."""
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

    def _views(self, frames: list[FrameInput], warnings: list[str]):
        masks, cams, yaws = [], [], []
        s = self.settings
        target = (0.0, 0.0, 0.08 * s.capture_radius_units)
        for f in frames:
            img = cv2.imread(str(f.path))
            if img is None:
                warnings.append(f"frame {f.index}: unreadable image, skipped")
                continue
            img = downscale_for_processing(img)
            mask = extract_silhouette(img, "auto")
            if not is_plausible(mask):
                warnings.append(f"frame {f.index}: no plausible foot silhouette, skipped")
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
        warnings: list[str] = []
        orbit = [f for f in frames if f.kind == ORBIT_KIND]
        topdown = [f for f in frames if f.kind == TOPDOWN_KIND]
        if len(orbit) < s.min_orbit_frames:
            raise ReconstructionError(f"need at least {s.min_orbit_frames} orbit frames, got {len(orbit)}")

        masks, cams, yaws = self._views(orbit, warnings)
        if len(masks) < s.min_orbit_frames:
            raise ReconstructionError(
                f"only {len(masks)} usable silhouettes (need {s.min_orbit_frames}); " + "; ".join(warnings)
            )
        ok, problems = validate_coverage(yaws, s.sector_deg, min_fraction=0.5, max_gap_deg=120.0)
        if not ok:
            raise ReconstructionError("insufficient angular coverage: " + " ".join(problems))
        _, soft = validate_coverage(yaws, s.sector_deg, min_fraction=0.75, max_gap_deg=60.0)
        warnings.extend(soft)

        r = s.capture_radius_units
        bounds = np.array([[-0.6 * r, 0.6 * r], [-0.6 * r, 0.6 * r], [0.0, 0.5 * r]])
        grid_units = carve_adaptive(masks, cams, bounds, s.coarse_resolution, s.voxel_resolution)
        unscaled = analyze_foot(grid_units, mesh=None, stations=40)
        length_units = unscaled.measurements.length_mm  # still in reconstruction units here

        topdown_info = None
        if topdown:
            img = cv2.imread(str(topdown[0].path))
            td = measure_topdown(img, paper or s.paper_size) if img is not None else None
            if td is not None:
                topdown_info = td.to_dict()
            else:
                warnings.append("top-down frame: paper sheet not detected; falling back to another scale source")

        if topdown_info is not None:
            scale, method, confidence = topdown_info["length_mm"] / length_units, "paper", "high"
        elif known_length_mm:
            scale, method, confidence = float(known_length_mm) / length_units, "known_length", "medium"
        else:
            scale, method, confidence = s.default_capture_radius_mm / r, "assumed", "low"
            warnings.append("No scale reference: measurements assume a 45 cm capture distance.")

        grid_mm = grid_units.scaled(scale)
        length_mm = length_units * scale
        grid_mm = clip_height(grid_mm, ANKLE_CUT_RATIO * length_mm)
        mesh = grid_to_mesh(grid_mm)
        geometry = analyze_foot(grid_mm, mesh)
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
        )


class UploadedMeshReconstructor:
    """Measure a mesh captured by a depth sensor (already metric)."""

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
