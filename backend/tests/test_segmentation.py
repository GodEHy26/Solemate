import cv2
import numpy as np
import pytest

from app.services.scanning.segmentation import extract_silhouette, is_plausible


def _scene(fg, bg):
    img = np.full((300, 400, 3), bg, np.uint8)
    cv2.ellipse(img, (200, 160), (90, 50), 20, 0, 360, fg, -1)
    cv2.circle(img, (20, 20), 6, fg, -1)
    return img


@pytest.mark.parametrize("fg,bg", [((60, 50, 45), (230, 230, 230)), ((235, 230, 225), (40, 40, 40))])
def test_polarity_and_largest_component(fg, bg):
    mask = extract_silhouette(_scene(fg, bg), "otsu")
    assert is_plausible(mask)
    assert mask[160, 200]
    assert not mask[20, 20]
    area = mask.sum()
    assert abs(area - np.pi * 90 * 50) / (np.pi * 90 * 50) < 0.05


def test_auto_falls_back_to_saturation():

    img = np.full((300, 400, 3), (128, 128, 128), np.uint8)
    cv2.ellipse(img, (200, 160), (90, 50), 0, 0, 360, (60, 120, 190), -1)
    mask = extract_silhouette(img, "auto")
    assert is_plausible(mask) and mask[160, 200]
