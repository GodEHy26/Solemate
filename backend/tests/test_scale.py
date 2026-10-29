import numpy as np
import pytest

from app.services.scanning.scale import detect_paper, measure_topdown, order_corners
from tests.synthetic import paper_scene


def test_order_corners():
    pts = np.array([[10, 90], [90, 90], [90, 10], [10, 10]])
    tl, tr, br, bl = order_corners(pts)
    assert tl.tolist() == [10, 10] and tr.tolist() == [90, 10]
    assert br.tolist() == [90, 90] and bl.tolist() == [10, 90]


@pytest.mark.parametrize("rotation", [0.0, 12.0, -25.0])
def test_paper_scale_measures_foot_in_mm(rotation):
    img = paper_scene(foot_length_mm=262.0, foot_width_mm=97.0, rotation_deg=rotation)
    assert detect_paper(img) is not None
    td = measure_topdown(img, "A4")
    assert td is not None
    assert td.length_mm == pytest.approx(262.0, rel=0.03)
    assert td.width_mm == pytest.approx(97.0, rel=0.04)
    assert len(td.contour_mm) > 10


def test_no_paper_returns_none():
    img = np.full((400, 600, 3), 80, np.uint8)
    assert measure_topdown(img, "A4") is None
