"""Application settings.

Every value can be overridden with an environment variable prefixed with
``SOLEMATE_`` (for example ``SOLEMATE_DATA_DIR=/var/solemate``) or a ``.env``
file in the backend directory.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOLEMATE_", env_file=".env", extra="ignore")

    app_name: str = "SoleMate API"
    version: str = "2.0.0"

    # Storage -------------------------------------------------------------
    data_dir: Path = BACKEND_DIR / "data_store"
    database_url: str = ""  # empty -> sqlite file inside data_dir
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Processing ------------------------------------------------------------
    # Run reconstruction inline in the request instead of a background task.
    sync_processing: bool = False

    # Preorders ---------------------------------------------------------------
    # Every product is a preorder: nothing is manufactured until it is ordered.
    preorder_ship_estimate: str = (
        "Estimated shipping: to be announced. We will email you before production starts."
    )
    terms_version: str = "2026-10-24"
    shipping_policy: str = (
        "Shipping and any taxes or duties are not included in the price shown. "
        "We will contact you about them before production starts."
    )

    # Payments (Stripe Checkout, hosted by Stripe) ------------------------------
    public_url: str = "http://localhost:5173"   # where the web app lives; used for Stripe return URLs
    stripe_secret_key: str = ""                 # sk_test_... or sk_live_...
    stripe_webhook_secret: str = ""             # whsec_...
    stripe_api_base: str = ""                   # tests only: point the SDK at a local fake

    # Operator details shown on the legal pages -------------------------------
    company_name: str = ""
    support_email: str = ""
    company_address: str = ""
    governing_law: str = ""                     # e.g. "the laws of the Republic of Korea"

    # Data retention ----------------------------------------------------------
    stale_session_hours: int = 24               # unfinished/failed scans are deleted after this
    unpaid_order_hours: int = 48                # orders nobody paid for are deleted after this

    # Scanning / reconstruction --------------------------------------------
    sector_deg: float = 15.0            # one coverage sector of the capture ring
    orbit_pitch_deg: float = 30.0       # default downward tilt of the phone
    min_orbit_frames: int = 8
    voxel_resolution: int = 128         # fine carve resolution (longest axis)
    coarse_resolution: int = 48
    camera_hfov_deg: float = 65.0       # typical phone main camera
    capture_radius_units: float = 1.0   # orbit radius in reconstruction units
    default_capture_radius_mm: float = 450.0  # used only when no scale reference exists
    paper_size: str = "A4"

    @property
    def payments_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

    @property
    def legal_configured(self) -> bool:
        return bool(self.company_name and self.support_email)

    @property
    def scans_dir(self) -> Path:
        return self.data_dir / "scans"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'solemate.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.scans_dir.mkdir(parents=True, exist_ok=True)
    return settings
