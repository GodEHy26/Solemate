import numpy as np
import pytest

from app.services.scanning.measurements import analyze_foot
from app.services.scanning.meshing import grid_to_mesh
from app.services.scanning.visual_hull import VoxelGrid


def _ellipsoid_grid(radii_mm, spacing=3.0, rotation_deg=0.0, flip=False):

    a, b, c = radii_mm
    th = np.radians(rotation_deg + (180.0 if flip else 0.0))
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    half = a + 2 * spacing
    xs = np.arange(-half, half, spacing)
    ys = np.arange(-half, half, spacing)
    zs = np.arange(0, c + 2 * spacing, spacing)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")

    xl = R[0, 0] * X + R[1, 0] * Y
    yl = R[0, 1] * X + R[1, 1] * Y
    scale_y = 1.0 + 0.25 * np.clip(xl / a, -1, 1)
    occ = (xl / a) ** 2 + (yl / (b * scale_y)) ** 2 + (Z / c) ** 2 <= 1.0
    return VoxelGrid(occ, np.array([xs[0], ys[0], zs[0]]), np.full(3, spacing))


@pytest.mark.parametrize("rotation,flip", [(0.0, False), (35.0, False), (0.0, True), (-120.0, True)])
def test_measurements_are_pose_invariant(rotation, flip):
    radii = (130.0, 45.0, 40.0)
    grid = _ellipsoid_grid(radii, rotation_deg=rotation, flip=flip)
    geo = analyze_foot(grid, grid_to_mesh(grid, smooth_iterations=0))
    m = geo.measurements
    assert m.length_mm == pytest.approx(2 * radii[0], rel=0.06)
    assert m.ball_width_mm > m.heel_width_mm
    assert m.ball_position_mm > m.length_mm / 2
    assert 0 < m.toe_height_mm <= m.instep_height_mm + 1e-6 or m.toe_height_mm < radii[2]
    assert m.instep_height_mm == pytest.approx(radii[2], rel=0.15)
    assert m.ball_girth_mm and m.ball_girth_mm > 2 * m.ball_width_mm
    assert len(geo.footprint_mm) >= 8
    xs = [p[0] for p in geo.footprint_mm]
    assert min(xs) >= -5 and max(xs) <= m.length_mm + 5
    assert geo.sections and all(s["points"] for s in geo.sections)


def test_last_vector_shape():
    grid = _ellipsoid_grid((130.0, 45.0, 40.0))
    geo = analyze_foot(grid)
    vec = geo.measurements.last_vector()
    assert len(vec) == 5 and all(v > 0 for v in vec)
