"""Scan quality checks.

Each check turns a measurable symptom into a ``ScanWarning`` with a plain-language message and a
fix. Severity ``block`` means we will not show a size or take an order from this scan; ``warn``
means we show a size range instead of one size and the customer must acknowledge it to order.

Thresholds live in ``THRESHOLDS`` and are documented in docs/SCAN_PIPELINE.md ("Warnings").
They were tuned on synthetic scans so that a clean capture raises nothing; re-tune them on real
scans before relying on them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .capture_plan import coverage_fraction, largest_gap_deg

BLOCK = "block"
WARN = "warn"

THRESHOLDS = {
    # incomplete orbit: the client's own standard (the server's hard floor is 50 % / 120 deg)
    "min_coverage": 0.75,
    "max_gap_deg": 60.0,
    # confusing background
    "fallback_fraction": 0.25,     # share of orbit frames that needed saturation/GrabCut or were rejected
    "size_jump_ratio": 1.5,        # outline area change between neighbouring frames (clean scans: <= 1.15)
    "size_jump_min_count": 2,      # one bad frame creates two jumps (both of its neighbours)
    "size_jump_neighbour_deg": 40.0,
    # measurements disagree: paper-photo width vs 3D-model width, beyond one voxel of quantisation
    "width_disagreement": 0.03,
    # left vs right foot length
    "left_right_mm": 8.0,
}


@dataclass
class ScanWarning:
    code: str
    severity: str  # "block" | "warn"
    message: str
    fix: str
    details: dict = field(default_factory=dict)
    side: str | None = None  # "left" | "right" | "both" when reported for a pair

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | str) -> "ScanWarning":
        if isinstance(d, str):  # profiles stored before structured warnings existed
            return cls("legacy", WARN, d, "If this looks wrong, rescan.")
        return cls(**{k: d.get(k) for k in ("code", "severity", "message", "fix", "side")}, details=d.get("details") or {})


@dataclass
class FrameStat:
    yaw_deg: float
    method: str          # otsu | saturation | grabcut | none
    area_fraction: float
    usable: bool


def confidence(warnings: list[ScanWarning]) -> str:
    if any(w.severity == BLOCK for w in warnings):
        return "low"
    if warnings:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# Side naming. Yaw 0 = camera in front of the toes, increasing counter-clockwise seen from above,
# so yaw 90 is on the foot's left (the person's left when standing on it).
# ---------------------------------------------------------------------------
def side_of(yaw_deg: float) -> str:
    y = yaw_deg % 360.0
    if y < 45 or y >= 315:
        return "toe end"
    if y < 135:
        return "left side"
    if y < 225:
        return "heel end"
    return "right side"


def largest_gap_center(yaws_deg: list[float]) -> float:
    ys = sorted(y % 360.0 for y in yaws_deg)
    if not ys:
        return 0.0
    best, center = -1.0, 0.0
    for i, y in enumerate(ys):
        nxt = ys[(i + 1) % len(ys)] + (360.0 if i == len(ys) - 1 else 0.0)
        if nxt - y > best:
            best, center = nxt - y, (y + (nxt - y) / 2) % 360.0
    return center


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_orbit(yaws_deg: list[float], sector_deg: float) -> list[ScanWarning]:
    frac = coverage_fraction(yaws_deg, sector_deg)
    gap = largest_gap_deg(yaws_deg)
    if frac >= THRESHOLDS["min_coverage"] and gap <= THRESHOLDS["max_gap_deg"]:
        return []
    side = side_of(largest_gap_center(yaws_deg))
    return [
        ScanWarning(
            "incomplete_orbit",
            WARN,
            "Part of your foot wasn't captured.",
            f"Retake the scan from the {side}.",
            {"coverage": round(frac, 3), "largest_gap_deg": round(gap, 1), "missing_side": side},
        )
    ]


def check_scale(scale_method: str) -> list[ScanWarning]:
    if scale_method in ("paper", "sensor"):
        return []
    return [
        ScanWarning(
            "paper_not_found",
            BLOCK,
            "We couldn't find the paper.",
            "Retake the top-down photo with the whole sheet flat and visible.",
            {"scale_method": scale_method},
        )
    ]


def check_background(frames: list[FrameStat]) -> list[ScanWarning]:
    if not frames:
        return []
    fallback = [f for f in frames if f.method != "otsu" or not f.usable]
    frac = len(fallback) / len(frames)

    usable = sorted((f for f in frames if f.usable and f.area_fraction > 0), key=lambda f: f.yaw_deg % 360)
    jumps = 0
    for i, f in enumerate(usable if len(usable) > 1 else []):
        g = usable[(i + 1) % len(usable)]
        sep = (g.yaw_deg - f.yaw_deg) % 360.0
        if sep == 0 or sep > THRESHOLDS["size_jump_neighbour_deg"]:
            continue
        ratio = max(f.area_fraction / g.area_fraction, g.area_fraction / f.area_fraction)
        if ratio > THRESHOLDS["size_jump_ratio"]:
            jumps += 1

    if frac < THRESHOLDS["fallback_fraction"] and jumps < THRESHOLDS["size_jump_min_count"]:
        return []
    return [
        ScanWarning(
            "confusing_background",
            WARN,
            "Your floor may be confusing the scan.",
            "Retake on a plain floor that contrasts with your skin.",
            {"fallback_frames": len(fallback), "frames": len(frames), "size_jumps": jumps},
        )
    ]


def check_agreement(paper_width_mm: float | None, model_width_mm: float, voxel_mm: float) -> list[ScanWarning]:
    """Compare two independent widths: the paper photo vs the 3D model.

    The model is scaled so its *length* equals the paper length, so length cannot disagree by
    construction. Width is measured independently in each, which makes it the real cross-check.
    The model width is only known to within one voxel, so it is treated as an interval.
    """
    if not paper_width_mm:
        return []
    lo, hi = model_width_mm - voxel_mm, model_width_mm
    if lo <= paper_width_mm <= hi:
        diff = 0.0
    else:
        diff = min(abs(paper_width_mm - lo), abs(paper_width_mm - hi)) / paper_width_mm
    if diff <= THRESHOLDS["width_disagreement"]:
        return []
    return [
        ScanWarning(
            "measurements_disagree",
            WARN,
            "Your measurements don't agree with each other.",
            "Please rescan.",
            {"paper_width_mm": round(paper_width_mm, 1), "model_width_mm": round(model_width_mm, 1), "difference_pct": round(100 * diff, 1)},
        )
    ]


def check_left_right(left_length_mm: float, right_length_mm: float) -> list[ScanWarning]:
    diff = abs(left_length_mm - right_length_mm)
    if diff <= THRESHOLDS["left_right_mm"]:
        return []
    longer = "left" if left_length_mm > right_length_mm else "right"
    return [
        ScanWarning(
            "left_right_mismatch",
            WARN,
            f"Your feet measured {diff:.0f} mm apart in length.",
            "A small difference is normal. Check both scans and rescan either foot if it looks wrong.",
            {"left_length_mm": round(left_length_mm, 1), "right_length_mm": round(right_length_mm, 1), "longer": longer},
            side="both",
        )
    ]
