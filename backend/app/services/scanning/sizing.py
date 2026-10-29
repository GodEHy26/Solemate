





from __future__ import annotations

from dataclasses import dataclass

MM_PER_INCH = 25.4


def round_half(value: float) -> float:
    return round(value * 2.0) / 2.0


@dataclass(frozen=True)
class WidthCategory:
    code: str
    label: str
    ratio: float

    def to_dict(self) -> dict:
        return {"code": self.code, "label": self.label, "ratio": round(self.ratio, 3)}



_WIDTH_BANDS = [
    (0.345, "B", "Narrow"),
    (0.380, "D", "Medium"),
    (0.400, "2E", "Wide"),
    (9.999, "4E", "Extra wide"),
]


def width_category(length_mm: float, ball_width_mm: float) -> WidthCategory:
    if length_mm <= 0:
        raise ValueError("length must be positive")
    ratio = ball_width_mm / length_mm
    for upper, code, label in _WIDTH_BANDS:
        if ratio < upper:
            return WidthCategory(code, label, ratio)
    return WidthCategory("4E", "Extra wide", ratio)


def sizes_from_length(length_mm: float) -> dict[str, float]:

    if length_mm <= 0:
        raise ValueError("length must be positive")
    inches = length_mm / MM_PER_INCH
    us_men = round_half(3.0 * inches - 22.0)
    return {
        "us_men": us_men,
        "us_women": us_men + 1.5,
        "uk": us_men - 1.0,
        "eu": round_half((length_mm / 10.0 + 1.5) * 1.5),
        "mondopoint_cm": round_half(length_mm / 10.0),
    }


def recommend_sizing(length_mm: float, ball_width_mm: float, toe_allowance_mm: float = 10.0) -> dict:

    foot = sizes_from_length(length_mm)
    shoe = sizes_from_length(length_mm + toe_allowance_mm)
    width = width_category(length_mm, ball_width_mm)
    return {
        "foot_length_mm": round(length_mm, 1),
        "toe_allowance_mm": toe_allowance_mm,
        "foot": foot,
        "recommended": shoe,
        "width": width.to_dict(),
        "notes": [
            "Sizes are chart conversions for orientation only; the custom last is built from the scan.",
            f"Recommended size includes {toe_allowance_mm:.0f} mm toe allowance.",
        ],
    }
