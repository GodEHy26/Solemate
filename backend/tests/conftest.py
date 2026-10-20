"""Test configuration: isolated data dir, inline processing, small voxel grids."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="solemate-test-")
os.environ.setdefault("SOLEMATE_DATA_DIR", _TMP)
os.environ.setdefault("SOLEMATE_SYNC_PROCESSING", "1")
os.environ.setdefault("SOLEMATE_VOXEL_RESOLUTION", "72")
os.environ.setdefault("SOLEMATE_COARSE_RESOLUTION", "32")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
