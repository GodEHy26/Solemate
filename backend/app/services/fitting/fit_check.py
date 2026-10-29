
from __future__ import annotations

import math

from ..scanning.quality import BLOCK, ScanWarning, check_left_right, confidence
from ..scanning.sizing import MM_PER_INCH, width_category

TOE_ALLOWANCE_MM = 10.0


def exact_sizes(foot_length_mm: float, toe_allowance_mm: float = TOE_ALLOWANCE_MM) -> dict[str, float]:

    shoe = foot_length_mm + toe_allowance_mm
    us = 3.0 * (shoe / MM_PER_INCH) - 22.0
    return {
        "us_men": us,
        "us_women": us + 1.5,
        "uk": us - 1.0,
        "eu": (shoe / 10.0 + 1.5) * 1.5,
        "mondopoint_cm": shoe / 10.0,
    }


def _half(x: float) -> float:
    return round(x * 2.0) / 2.0


def _bracket(x: float) -> tuple[float, float]:
    lo = math.floor(x * 2.0 + 1e-9) / 2.0
    return lo, lo + 0.5


def size_summary(foot_length_mm: float, ball_width_mm: float, warnings: list[ScanWarning]) -> dict:
    blocking = [w for w in warnings if w.severity == BLOCK]
    if blocking:
        return {
            "mode": "none",
            "explanation": "We can't give you a size from this scan. " + " ".join(w.fix for w in blocking),
            "sizes": None,
            "width": None,
        }
    exact = exact_sizes(foot_length_mm)
    width = width_category(foot_length_mm, ball_width_mm).to_dict()
    if warnings:
        sizes = {k: dict(zip(("low", "high"), _bracket(v))) for k, v in exact.items()}
        reasons = "; ".join(w.message.rstrip(".") for w in warnings)
        return {
            "mode": "range",
            "explanation": f"Your scan has a warning ({reasons}), so we show the two sizes your foot falls between. A clean rescan gives one size.",
            "sizes": sizes,
            "width": width,
        }
    sizes = {k: {"low": _half(v), "high": _half(v)} for k, v in exact.items()}
    return {"mode": "single", "explanation": f"Includes {TOE_ALLOWANCE_MM:.0f} mm of toe room.", "sizes": sizes, "width": width}


def pair_check(left: dict, right: dict) -> dict:





    warnings: list[ScanWarning] = []
    for side, foot in (("left", left), ("right", right)):
        for w in foot["warnings"]:
            warnings.append(ScanWarning(w.code, w.severity, w.message, w.fix, w.details, side=side))
    warnings += check_left_right(left["length_mm"], right["length_mm"])
    longer = left if left["length_mm"] >= right["length_mm"] else right
    wider = max(left["ball_width_mm"], right["ball_width_mm"])
    blocked = any(w.severity == BLOCK for w in warnings)
    return {
        "confidence": confidence(warnings),
        "blocked": blocked,
        "needs_acknowledgement": bool(warnings) and not blocked,
        "warnings": [w.to_dict() for w in warnings],
        "size": size_summary(longer["length_mm"], wider, warnings),
    }
