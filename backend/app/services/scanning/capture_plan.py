
from __future__ import annotations

from dataclasses import asdict, dataclass

TOPDOWN_KIND = "topdown"
ORBIT_KIND = "orbit"


@dataclass(frozen=True)
class CapturePose:
    index: int
    kind: str
    yaw_deg: float
    pitch_deg: float
    instruction: str

    def to_dict(self) -> dict:
        return asdict(self)


def sector_count(sector_deg: float) -> int:
    if sector_deg <= 0 or sector_deg > 180:
        raise ValueError("sector_deg must be in (0, 180]")
    return int(round(360.0 / sector_deg))


def sector_of(yaw_deg: float, sector_deg: float) -> int:

    n = sector_count(sector_deg)
    return int((yaw_deg % 360.0) // (360.0 / n)) % n


def build_capture_plan(
    sector_deg: float = 15.0,
    pitch_deg: float = 30.0,
    include_topdown: bool = True,
) -> list[CapturePose]:

    poses: list[CapturePose] = []
    idx = 0
    if include_topdown:
        poses.append(
            CapturePose(
                index=idx,
                kind=TOPDOWN_KIND,
                yaw_deg=0.0,
                pitch_deg=90.0,
                instruction=(
                    "Stand on a sheet of A4 or Letter paper. Hold the phone flat above "
                    "your foot so the whole sheet is in frame, then capture."
                ),
            )
        )
        idx += 1
    n = sector_count(sector_deg)
    for i in range(n):
        yaw = i * 360.0 / n
        poses.append(
            CapturePose(
                index=idx,
                kind=ORBIT_KIND,
                yaw_deg=yaw,
                pitch_deg=pitch_deg,
                instruction=f"Move slowly around your foot ({int(yaw)}°), keeping it inside the ring.",
            )
        )
        idx += 1
    return poses


def covered_sectors(yaws_deg: list[float], sector_deg: float = 15.0) -> set[int]:
    return {sector_of(y, sector_deg) for y in yaws_deg}


def coverage_fraction(yaws_deg: list[float], sector_deg: float = 15.0) -> float:
    n = sector_count(sector_deg)
    return len(covered_sectors(yaws_deg, sector_deg)) / n


def missing_sectors(yaws_deg: list[float], sector_deg: float = 15.0) -> list[int]:
    n = sector_count(sector_deg)
    have = covered_sectors(yaws_deg, sector_deg)
    return [i for i in range(n) if i not in have]


def largest_gap_deg(yaws_deg: list[float]) -> float:

    if not yaws_deg:
        return 360.0
    ys = sorted(y % 360.0 for y in yaws_deg)
    gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    gaps.append(ys[0] + 360.0 - ys[-1])
    return max(gaps)


def validate_coverage(
    yaws_deg: list[float],
    sector_deg: float = 15.0,
    min_fraction: float = 0.75,
    max_gap_deg: float = 60.0,
) -> tuple[bool, list[str]]:

    problems: list[str] = []
    frac = coverage_fraction(yaws_deg, sector_deg)
    if frac < min_fraction:
        problems.append(
            f"Only {frac:.0%} of the ring is covered; at least {min_fraction:.0%} is required."
        )
    gap = largest_gap_deg(yaws_deg)
    if gap > max_gap_deg:
        problems.append(f"There is a {gap:.0f}° gap in the sweep; keep gaps under {max_gap_deg:.0f}°.")
    return (not problems), problems
