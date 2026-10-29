
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="solemate-test-")
os.environ.setdefault("SOLEMATE_DATA_DIR", _TMP)
os.environ.setdefault("SOLEMATE_SYNC_PROCESSING", "1")
os.environ.setdefault("SOLEMATE_VOXEL_RESOLUTION", "72")
os.environ.setdefault("SOLEMATE_COARSE_RESOLUTION", "32")
os.environ.setdefault("SOLEMATE_STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("SOLEMATE_STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
os.environ.setdefault("SOLEMATE_PUBLIC_URL", "https://shop.example.com")
os.environ.setdefault("SOLEMATE_COMPANY_NAME", "Test Co")
os.environ.setdefault("SOLEMATE_SUPPORT_EMAIL", "help@example.com")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
