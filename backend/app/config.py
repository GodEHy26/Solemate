
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

    data_dir: Path = BACKEND_DIR / "data_store"
    database_url: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    sync_processing: bool = False

    preorder_ship_estimate: str = (
        "Estimated shipping: to be announced. We will email you before production starts."
    )
    terms_version: str = "2026-10-24"
    shipping_policy: str = (
        "Shipping and any taxes or duties are not included in the price shown. "
        "We will contact you about them before production starts."
    )

    public_url: str = "http://localhost:5173"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_api_base: str = ""

    company_name: str = "Ethan Hahn"
    support_email: str = "godehy26@gmail.com"
    company_address: str = ""
    governing_law: str = ""

    stale_session_hours: int = 24
    unpaid_order_hours: int = 48

    sector_deg: float = 15.0
    orbit_pitch_deg: float = 30.0
    min_orbit_frames: int = 8
    voxel_resolution: int = 128
    coarse_resolution: int = 48
    camera_hfov_deg: float = 65.0
    capture_radius_units: float = 1.0
    default_capture_radius_mm: float = 450.0
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
