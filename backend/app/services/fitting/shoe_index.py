"""KD-tree over 5-D last measurement vectors.

Carried over from the IB IA (``models/shoe_index.py``) where it indexed stock
basketball shoes. Here it indexes *reference lasts* so a scanned foot can be
matched to the closest base last before grading and custom adjustments.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

MeasurementVector = Tuple[float, float, float, float, float]


def _euclidean_sq(a: MeasurementVector, b: MeasurementVector) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


@dataclass
class _KDNode:
    point: MeasurementVector
    payload: dict
    axis: int
    left: Optional["_KDNode"] = None
    right: Optional["_KDNode"] = None


class ShoeIndex:
    """KD-tree supporting k-nearest-neighbour queries in measurement space."""

    def __init__(self, measurements: Sequence[Tuple[MeasurementVector, dict]]):
        points = [item for item in measurements if self._valid_vector(item[0])]
        self._dimension = 5
        self._root = self._build(points)

    @staticmethod
    def _valid_vector(vec: MeasurementVector) -> bool:
        return len(vec) == 5 and all(value is not None for value in vec)

    def _build(self, points: Sequence[Tuple[MeasurementVector, dict]], depth: int = 0) -> Optional[_KDNode]:
        if not points:
            return None
        axis = depth % self._dimension
        sorted_points = sorted(points, key=lambda item: item[0][axis])
        median_idx = len(sorted_points) // 2
        median_point, median_payload = sorted_points[median_idx]
        return _KDNode(
            point=median_point,
            payload=median_payload,
            axis=axis,
            left=self._build(sorted_points[:median_idx], depth + 1),
            right=self._build(sorted_points[median_idx + 1 :], depth + 1),
        )

    def nearest_neighbors(self, target: MeasurementVector, k: int = 3) -> List[Tuple[float, dict]]:
        if self._root is None:
            return []
        best: List[Tuple[float, dict]] = []

        def search(node: Optional[_KDNode]) -> None:
            if node is None:
                return
            dist = _euclidean_sq(node.point, target)
            best.append((dist, node.payload))
            best.sort(key=lambda item: item[0])
            if len(best) > k:
                best.pop()
            axis = node.axis
            diff = target[axis] - node.point[axis]
            first, second = (node.left, node.right) if diff < 0 else (node.right, node.left)
            search(first)
            if len(best) < k or diff**2 < best[-1][0]:
                search(second)

        search(self._root)
        return sorted(best, key=lambda item: item[0])

    def is_empty(self) -> bool:
        return self._root is None
