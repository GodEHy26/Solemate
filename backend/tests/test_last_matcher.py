from app.services.fitting.last_matcher import build_last_spec, grade_last, load_reference_lasts
from app.services.fitting.shoe_index import ShoeIndex
from app.services.scanning.measurements import FootMeasurements


def _foot(length=265.0, ball=101.0):
    return FootMeasurements(
        length_mm=length, ball_width_mm=ball, heel_width_mm=64.0, waist_width_mm=80.0, toe_width_mm=78.0,
        instep_height_mm=66.0, ball_height_mm=38.0, toe_height_mm=24.0, ball_girth_mm=250.0, waist_girth_mm=235.0,
        instep_girth_mm=255.0, ball_position_mm=190.0, waist_position_mm=150.0, instep_position_mm=130.0, volume_cm3=900.0,
    )


def test_kd_tree_nearest():
    index = ShoeIndex([((1, 1, 1, 1, 1), {"id": "a"}), ((5, 5, 5, 5, 5), {"id": "b"}), ((9, 9, 9, 9, 9), {"id": "c"})])
    near = index.nearest_neighbors((4, 4, 4, 4, 4), k=2)
    assert [p["id"] for _, p in near] == ["b", "a"]
    assert ShoeIndex([]).is_empty()


def test_grading_moves_length_a_third_inch_per_size():
    base = load_reference_lasts()[0]
    up = grade_last(base, base["base_size_us"] + 1)
    assert abs((up["length_mm"] - base["length_mm"]) - 25.4 / 3) < 1e-6


def test_last_spec_respects_family_and_allowances():
    spec = build_last_spec(_foot(), family="run")
    assert spec["base_last"]["family"] == "run"
    assert spec["target_mm"]["length_mm"] == 275.0  # 265 + 10 mm toe room
    assert spec["graded_last_mm"]["length_mm"] + spec["adjustments_mm"]["length_mm"] == spec["target_mm"]["length_mm"]
    assert spec["graded_size_us"] >= 9.5
    wide = build_last_spec(_foot(ball=112.0), family="run")
    assert wide["base_last"]["id"] == "run-wide"
