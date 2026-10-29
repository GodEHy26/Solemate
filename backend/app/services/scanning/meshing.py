"""Voxel grid -> triangle mesh (marching cubes) and mesh export."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from skimage import measure

from .visual_hull import ReconstructionError, VoxelGrid

SUPPORTED_EXPORTS = (".glb", ".obj", ".ply", ".stl")


def grid_to_mesh(grid: VoxelGrid, smooth_iterations: int = 10) -> trimesh.Trimesh:
    """Extract the iso-surface of the occupancy grid as a watertight mesh."""
    if not grid.occupancy.any():
        raise ReconstructionError("cannot mesh an empty voxel grid")
    volume = np.pad(grid.occupancy.astype(np.float32), 1)  # zero border closes the surface
    verts, faces, _normals, _values = measure.marching_cubes(volume, level=0.5, spacing=tuple(grid.spacing))
    verts = verts + (grid.origin - grid.spacing)  # undo padding offset
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    if smooth_iterations > 0 and len(mesh.vertices) > 0:
        trimesh.smoothing.filter_taubin(mesh, iterations=smooth_iterations)
    mesh.fix_normals()
    return mesh


def load_mesh(path: str | Path, units: str = "mm") -> trimesh.Trimesh:
    """Load a mesh produced elsewhere (for example an ARKit/LiDAR app) and convert to mm."""
    loaded = trimesh.load(str(path), force="mesh")
    if not isinstance(loaded, trimesh.Trimesh):
        raise ReconstructionError("file did not contain a triangle mesh")
    factor = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}.get(units.lower())
    if factor is None:
        raise ValueError(f"unsupported units: {units}")
    if factor != 1.0:
        loaded.apply_scale(factor)
    return loaded


def export_mesh(mesh: trimesh.Trimesh, path: str | Path) -> Path:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_EXPORTS:
        raise ValueError(f"unsupported mesh format: {path.suffix}")
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(path))
    return path


def mesh_to_grid(mesh: trimesh.Trimesh, resolution: int = 128) -> VoxelGrid:
    """Voxelise a closed mesh (used for uploaded meshes so measurements share one code path)."""
    bounds = mesh.bounds
    extent = bounds[1] - bounds[0]
    pitch = float(extent.max()) / float(resolution)
    vox = mesh.voxelized(pitch).fill()
    occupancy = np.asarray(vox.matrix, dtype=bool)
    origin = np.asarray(vox.translation, dtype=np.float64)
    return VoxelGrid(occupancy, origin, np.full(3, pitch))
