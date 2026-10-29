




from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin, tan

import numpy as np


@dataclass(frozen=True)
class Camera:
    K: np.ndarray
    R: np.ndarray
    t: np.ndarray
    width: int
    height: int

    def project(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:

        pts = np.asarray(points, dtype=np.float64)
        cam = pts @ self.R.T + self.t
        z = cam[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = self.K[0, 0] * cam[:, 0] / z + self.K[0, 2]
            v = self.K[1, 1] * cam[:, 1] / z + self.K[1, 2]
        return np.stack([u, v], axis=1), z

    @property
    def center(self) -> np.ndarray:

        return -self.R.T @ self.t


def intrinsics(width: int, height: int, hfov_deg: float) -> np.ndarray:
    f = (width / 2.0) / tan(radians(hfov_deg) / 2.0)
    return np.array([[f, 0.0, width / 2.0], [0.0, f, height / 2.0], [0.0, 0.0, 1.0]])


def look_at(eye, target, up=(0.0, 0.0, 1.0)) -> tuple[np.ndarray, np.ndarray]:
    eye = np.asarray(eye, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, up)
    if np.linalg.norm(right) < 1e-9:
        right = np.cross(forward, np.array([0.0, 1.0, 0.0]))
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    R = np.stack([right, down, forward])
    t = -R @ eye
    return R, t


def orbit_camera(
    yaw_deg: float,
    pitch_deg: float,
    radius: float,
    target,
    width: int,
    height: int,
    hfov_deg: float,
) -> Camera:





    pitch_deg = max(-89.5, min(89.5, pitch_deg))
    yaw, pitch = radians(yaw_deg), radians(pitch_deg)
    target = np.asarray(target, dtype=np.float64)
    eye = target + radius * np.array([cos(pitch) * cos(yaw), cos(pitch) * sin(yaw), sin(pitch)])
    R, t = look_at(eye, target)
    return Camera(intrinsics(width, height, hfov_deg), R, t, int(width), int(height))
