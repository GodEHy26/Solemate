from app.services.scanning import capture_plan as cp


def test_plan_has_topdown_then_full_ring():
    plan = cp.build_capture_plan(sector_deg=15, pitch_deg=30)
    assert plan[0].kind == "topdown"
    orbit = [p for p in plan if p.kind == "orbit"]
    assert len(orbit) == 24
    assert orbit[0].yaw_deg == 0 and orbit[-1].yaw_deg == 345


def test_sector_wraps_and_coverage():
    assert cp.sector_of(0, 15) == 0
    assert cp.sector_of(359.9, 15) == 23
    assert cp.sector_of(-5, 15) == 23
    yaws = [i * 15 for i in range(24)]
    assert cp.coverage_fraction(yaws, 15) == 1.0
    assert cp.missing_sectors(yaws[:12], 15) == list(range(12, 24))


def test_validate_coverage_flags_gaps():
    ok, problems = cp.validate_coverage([0, 20, 40, 60], 15)
    assert not ok and problems
    ok, problems = cp.validate_coverage([i * 20 for i in range(18)], 15, min_fraction=0.75, max_gap_deg=60)
    assert ok, problems
    assert cp.largest_gap_deg([]) == 360
