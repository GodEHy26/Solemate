import numpy as np

from app.services.scanning.cameras import orbit_camera


def test_target_projects_to_image_centre_from_any_yaw():
    for yaw in (0, 45, 123, 270):
        cam = orbit_camera(yaw, 30, 1.0, (0, 0, 0.1), 640, 480, 65)
        uv, z = cam.project(np.array([[0, 0, 0.1]]))
        assert z[0] > 0
        assert np.allclose(uv[0], [320, 240], atol=1e-6)


def test_image_axes_follow_opencv_convention():
    cam = orbit_camera(0, 0, 1.0, (0, 0, 0), 640, 480, 65)
    uv_up, _ = cam.project(np.array([[0, 0, 0.1]]))
    uv_right, _ = cam.project(np.array([[0, 0.1, 0]]))
    assert uv_up[0, 1] < 240
    assert uv_right[0, 0] > 320
    assert np.allclose(cam.center, [1, 0, 0])
