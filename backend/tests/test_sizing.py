import pytest

from app.services.scanning.sizing import recommend_sizing, sizes_from_length, width_category


def test_us_size_from_length():
    assert sizes_from_length(270.0)["us_men"] == 10.0
    assert sizes_from_length(254.0)["us_men"] == 8.0
    assert sizes_from_length(270.0)["eu"] == pytest.approx(42.5, abs=0.5)


def test_width_bands():
    assert width_category(270, 92).code == "B"
    assert width_category(270, 100).code == "D"
    assert width_category(270, 105).code == "2E"
    assert width_category(270, 112).code == "4E"


def test_recommendation_includes_toe_room():
    rec = recommend_sizing(270.0, 100.0)
    assert rec["recommended"]["us_men"] >= rec["foot"]["us_men"]
    assert rec["width"]["code"] == "D"
    with pytest.raises(ValueError):
        sizes_from_length(0)
