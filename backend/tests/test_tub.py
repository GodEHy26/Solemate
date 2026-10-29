import numpy as np
import pytest

from app.services.insole.tub import TubParams, bed_fit, build_tub


def foot_like_contour(length=260.0, ball=100.0, big_toe_side=1.0):
    """Closed outline in foot coordinates (heel x=0 -> toe), wider toe end, longer on one side."""
    t = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    x = length / 2 * (1 - np.cos(t))
    half = ball / 2 * np.sin(t) * (0.65 + 0.35 * (x / length))
    x = x + 6 * big_toe_side * np.sign(np.sin(t)) * (x / length) ** 8  # one side reaches further
    return np.stack([x, half], axis=1)


def test_tub_is_watertight_and_sized():
    c = foot_like_contour()
    p = TubParams()
    res = build_tub(c, float(c[:, 0].max()), 100.0, p)
    m = res.mesh
    assert m.is_watertight
    assert m.volume > 0
    lo, hi = m.bounds
    assert hi[2] == pytest.approx(p.heel_cup_height_mm, abs=0.5)
    assert lo[2] == pytest.approx(0.0, abs=1e-6)
    # inside length = foot + toe room (+ side offset at both ends), within a few mm
    assert res.inner_length_mm == pytest.approx(c[:, 0].max() + p.toe_allowance_mm + 2 * p.side_allowance_mm, abs=4)


@pytest.mark.parametrize("side,expected", [(1.0, "+y"), (-1.0, "-y")])
def test_medial_side_follows_longest_toe(side, expected):
    c = foot_like_contour(big_toe_side=side)
    res = build_tub(c, float(c[:, 0].max()), 100.0)
    assert res.medial_side == expected


def test_bed_fit():
    rect = np.array([[0, 0], [280, 0], [280, 110], [0, 110]], float)
    assert bed_fit(rect, 300, 300) == 0
    assert bed_fit(rect, 220, 220) is None
