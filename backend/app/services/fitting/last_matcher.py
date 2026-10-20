"""Turn foot measurements into a custom last specification.

1. Pick the closest *reference last* (optionally restricted to the last family
   a shoe model is built on) with the KD-tree.
2. Grade it to the customer's length (standard 1/3 inch per full US size).
3. Record the per-dimension deltas between the graded last and the scanned
   foot plus fit allowances. The result is what a last maker / 3D-printing
   step needs to produce the customer's last.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..scanning.measurements import FootMeasurements
from ..scanning.sizing import round_half
from .shoe_index import ShoeIndex

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "reference_lasts.json"

LENGTH_GRADE_MM_PER_SIZE = 25.4 / 3.0   # 8.47 mm
WIDTH_GRADE_MM_PER_SIZE = 2.0
HEIGHT_GRADE_MM_PER_SIZE = 1.0
POSITION_GRADE_MM_PER_SIZE = 4.5

DEFAULT_ALLOWANCES_MM = {
    "length": 10.0,       # toe room
    "ball_width": 2.0,    # upper stretch / sock
    "toe_width": 3.0,
    "toe_height": 3.0,
    "waist_position": 0.0,
}


def _vector(last: dict) -> tuple[float, float, float, float, float]:
    return (
        float(last["length_mm"]),
        float(last["ball_width_mm"]),
        float(last["toe_width_mm"]),
        float(last["toe_height_mm"]),
        float(last["waist_position_mm"]),
    )


@lru_cache
def load_reference_lasts() -> list[dict]:
    with DATA_FILE.open() as fh:
        return json.load(fh)["lasts"]


def build_index(family: str | None = None) -> ShoeIndex:
    lasts = [l for l in load_reference_lasts() if family is None or l.get("family") == family]
    return ShoeIndex([(_vector(l), l) for l in lasts])


def grade_last(last: dict, target_size: float) -> dict:
    """Scale a reference last from its base size to ``target_size`` (US men's)."""
    steps = target_size - float(last["base_size_us"])
    return {
        "length_mm": last["length_mm"] + steps * LENGTH_GRADE_MM_PER_SIZE,
        "ball_width_mm": last["ball_width_mm"] + steps * WIDTH_GRADE_MM_PER_SIZE,
        "toe_width_mm": last["toe_width_mm"] + steps * WIDTH_GRADE_MM_PER_SIZE * 0.8,
        "toe_height_mm": last["toe_height_mm"] + steps * HEIGHT_GRADE_MM_PER_SIZE,
        "waist_position_mm": last["waist_position_mm"] + steps * POSITION_GRADE_MM_PER_SIZE,
    }


def build_last_spec(
    foot: FootMeasurements,
    family: str | None = None,
    allowances: dict[str, float] | None = None,
) -> dict:
    """Return the custom last specification for one foot."""
    allow = {**DEFAULT_ALLOWANCES_MM, **(allowances or {})}
    index = build_index(family)
    if index.is_empty():
        index = build_index(None)
    if index.is_empty():
        raise RuntimeError("no reference lasts available")

    target_length = foot.length_mm + allow["length"]
    # Query on a length-normalised foot so proportions, not size, drive the match.
    scale = 1.0
    matches = index.nearest_neighbors(foot.last_vector(), k=3)
    base = matches[0][1]
    scale = base["length_mm"] / max(foot.length_mm, 1.0)
    proportional = tuple(v * scale for v in foot.last_vector())
    matches = index.nearest_neighbors(proportional, k=3)
    base = matches[0][1]

    size = round_half(base["base_size_us"] + (target_length - base["length_mm"]) / LENGTH_GRADE_MM_PER_SIZE)
    graded = grade_last(base, size)

    targets = {
        "length_mm": foot.length_mm + allow["length"],
        "ball_width_mm": foot.ball_width_mm + allow["ball_width"],
        "toe_width_mm": foot.toe_width_mm + allow["toe_width"],
        "toe_height_mm": foot.toe_height_mm + allow["toe_height"],
        "waist_position_mm": foot.waist_position_mm + allow["waist_position"],
    }
    adjustments = {k: round(targets[k] - graded[k], 1) for k in targets}

    return {
        "base_last": {
            "id": base["id"],
            "name": base["name"],
            "family": base.get("family"),
            "base_size_us": base["base_size_us"],
        },
        "graded_size_us": size,
        "graded_last_mm": {k: round(v, 1) for k, v in graded.items()},
        "target_mm": {k: round(v, 1) for k, v in targets.items()},
        "adjustments_mm": adjustments,
        "allowances_mm": allow,
        "girths_mm": {
            "ball": foot.ball_girth_mm,
            "waist": foot.waist_girth_mm,
            "instep": foot.instep_girth_mm,
        },
        "alternatives": [
            {"id": m[1]["id"], "name": m[1]["name"], "distance": round(m[0] ** 0.5, 1)} for m in matches[1:]
        ],
    }
