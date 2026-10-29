







from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from skimage.measure import label

from .cameras import Camera


class ReconstructionError(RuntimeError):


    def __init__(self, message: str, warnings: list | None = None):
        super().__init__(message)
        self.warnings = warnings or []


@dataclass
class VoxelGrid:
    occupancy: np.ndarray
    origin: np.ndarray
    spacing: np.ndarray

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(int(s) for s in self.occupancy.shape)  # type: ignore[return-value]

    def occupied_points(self) -> np.ndarray:
        idx = np.argwhere(self.occupancy)
        return self.origin + idx * self.spacing

    def bounds(self) -> np.ndarray:

        pts = self.occupied_points()
        if len(pts) == 0:
            raise ReconstructionError("voxel grid is empty")
        lo = pts.min(axis=0) - self.spacing / 2
        hi = pts.max(axis=0) + self.spacing / 2
        return np.stack([lo, hi], axis=1)

    def volume(self) -> float:
        return float(self.occupancy.sum() * np.prod(self.spacing))

    def scaled(self, factor: float) -> "VoxelGrid":
        return VoxelGrid(self.occupancy.copy(), self.origin * factor, self.spacing * factor)

    def transformed(self, R: np.ndarray, offset: np.ndarray) -> np.ndarray:

        return self.occupied_points() @ R.T + offset


def make_grid(bounds: np.ndarray, resolution: int) -> tuple[np.ndarray, tuple[int, int, int], np.ndarray, np.ndarray]:

    bounds = np.asarray(bounds, dtype=np.float64)
    extent = bounds[:, 1] - bounds[:, 0]
    if np.any(extent <= 0):
        raise ValueError("bounds must have positive extent on every axis")
    cell = float(extent.max()) / float(resolution)
    counts = np.maximum(1, np.ceil(extent / cell).astype(int))
    spacing = np.full(3, cell)
    origin = bounds[:, 0] + spacing / 2
    axes = [origin[i] + np.arange(counts[i]) * spacing[i] for i in range(3)]
    gx, gy, gz = np.meshgrid(*axes, indexing="ij")
    centers = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    return centers, (int(counts[0]), int(counts[1]), int(counts[2])), origin, spacing


def carve(
    masks: list[np.ndarray],
    cameras: list[Camera],
    bounds: np.ndarray,
    resolution: int,
    carve_outside_image: bool = False,
    min_observations: int = 1,
) -> VoxelGrid:







    if len(masks) != len(cameras):
        raise ValueError("masks and cameras must have the same length")
    if not masks:
        raise ValueError("at least one view is required")

    centers, shape, origin, spacing = make_grid(bounds, resolution)
    occ = np.ones(len(centers), dtype=bool)
    observations = np.zeros(len(centers), dtype=np.int32)

    for mask, cam in zip(masks, cameras):
        mask_b = np.asarray(mask).astype(bool)
        if mask_b.shape != (cam.height, cam.width):
            raise ValueError("mask shape does not match camera image size")
        uv, depth = cam.project(centers)
        u = np.rint(uv[:, 0]).astype(np.int64)
        v = np.rint(uv[:, 1]).astype(np.int64)
        inside = (depth > 0) & (u >= 0) & (u < cam.width) & (v >= 0) & (v < cam.height)
        hit = np.zeros(len(centers), dtype=bool)
        hit[inside] = mask_b[v[inside], u[inside]]
        observations += inside
        if carve_outside_image:
            occ &= hit
        else:
            occ &= hit | ~inside

    occ &= observations >= min_observations
    return VoxelGrid(occ.reshape(shape), origin, spacing)


def largest_component(grid: VoxelGrid) -> VoxelGrid:

    if not grid.occupancy.any():
        return grid
    labels = label(grid.occupancy, connectivity=1)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    keep = labels == int(np.argmax(counts))
    return VoxelGrid(keep, grid.origin.copy(), grid.spacing.copy())


def carve_adaptive(
    masks: list[np.ndarray],
    cameras: list[Camera],
    initial_bounds: np.ndarray,
    coarse_resolution: int = 48,
    fine_resolution: int = 128,
    pad_fraction: float = 0.08,
) -> VoxelGrid:

    coarse = largest_component(carve(masks, cameras, initial_bounds, coarse_resolution))
    if not coarse.occupancy.any():
        raise ReconstructionError("No voxels survived carving. Check silhouettes and camera poses.")
    b = coarse.bounds()
    extent = b[:, 1] - b[:, 0]
    pad = extent * pad_fraction + coarse.spacing
    tight = np.stack([b[:, 0] - pad, b[:, 1] + pad], axis=1)
    init = np.asarray(initial_bounds, dtype=np.float64)
    tight[:, 0] = np.maximum(tight[:, 0], init[:, 0])
    tight[:, 1] = np.minimum(tight[:, 1], init[:, 1])
    fine = largest_component(carve(masks, cameras, tight, fine_resolution))
    if not fine.occupancy.any():
        raise ReconstructionError("Fine carve produced an empty volume.")
    return fine
