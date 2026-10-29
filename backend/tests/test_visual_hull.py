import numpy as np
import pytest

from app.services.scanning.visual_hull import ReconstructionError, carve, carve_adaptive
from tests.synthetic import ellipsoid_surface, orbit_rig, render_silhouette

RADII = (0.13, 0.05, 0.04)
CENTER = (0.0, 0.0, 0.04)


def _views(n=20, pitch=30.0):
    pts = ellipsoid_surface(CENTER, RADII)
    yaws, cams = orbit_rig(n, pitch, 1.0, (0, 0, 0.08), 400, 300, 65)
    masks = [render_silhouette(c, pts) for c in cams]
    return masks, cams


def test_hull_recovers_ellipsoid_extents():
    masks, cams = _views()
    bounds = np.array([[-0.6, 0.6], [-0.6, 0.6], [0.0, 0.5]])
    grid = carve_adaptive(masks, cams, bounds, coarse_resolution=32, fine_resolution=80)
    b = grid.bounds()
    extents = b[:, 1] - b[:, 0]
    expected = 2 * np.array(RADII)

    assert np.all(extents >= expected * 0.95)
    assert np.all(extents <= expected * 1.20)
    assert b[2, 0] == pytest.approx(0.0, abs=grid.spacing[2])


def test_carve_rejects_mismatched_inputs():
    masks, cams = _views(4)
    with pytest.raises(ValueError):
        carve(masks[:2], cams, np.array([[-1, 1], [-1, 1], [0, 1]]), 16)


def test_empty_masks_raise():
    masks, cams = _views(6)
    empty = [np.zeros_like(m) for m in masks]
    with pytest.raises(ReconstructionError):
        carve_adaptive(empty, cams, np.array([[-0.6, 0.6], [-0.6, 0.6], [0.0, 0.5]]), 16, 32)
