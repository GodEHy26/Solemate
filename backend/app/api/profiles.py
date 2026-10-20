"""Foot profiles: measurements, meshes and the custom last specification."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session

from ..database import get_session
from ..db_models import FootProfile
from ..schemas import ProfileOut
from ..services.catalog.loader import get_shoe
from ..services.fitting.last_matcher import build_last_spec
from ..services.scanning.measurements import FootMeasurements

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

MESH_MEDIA = {"glb": "model/gltf-binary", "obj": "text/plain"}


def _load(db: Session, profile_id: str) -> FootProfile:
    profile = db.get(FootProfile, profile_id)
    if profile is None:
        raise HTTPException(404, "foot profile not found")
    return profile


def _measurements(profile: FootProfile) -> FootMeasurements:
    return FootMeasurements(**json.loads(profile.measurements_json))


def to_out(profile: FootProfile) -> ProfileOut:
    profiles = json.loads(profile.profiles_json or "{}")
    return ProfileOut(
        id=profile.id,
        scan_session_id=profile.scan_session_id,
        side=profile.side,
        source=profile.source,
        scale_method=profile.scale_method,
        scale_confidence=profile.scale_confidence,
        measurements=json.loads(profile.measurements_json),
        sizing=json.loads(profile.sizing_json),
        footprint_mm=json.loads(profile.footprint_json),
        width_profile=profiles.get("width", []),
        height_profile=profiles.get("height", []),
        topdown=profiles.get("topdown"),
        sections=json.loads(profile.sections_json),
        warnings=json.loads(profile.warnings_json),
        mesh_urls={ext: f"/api/profiles/{profile.id}/mesh.{ext}" for ext in MESH_MEDIA},
        created_at=profile.created_at,
    )


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: str, db: Session = Depends(get_session)) -> ProfileOut:
    return to_out(_load(db, profile_id))


@router.get("/{profile_id}/mesh.{ext}")
def get_mesh(profile_id: str, ext: str, db: Session = Depends(get_session)) -> FileResponse:
    profile = _load(db, profile_id)
    if ext not in MESH_MEDIA:
        raise HTTPException(404, "unsupported mesh format")
    path = profile.mesh_glb_path if ext == "glb" else profile.mesh_obj_path
    if not path or not Path(path).exists():
        raise HTTPException(404, "mesh file missing")
    return FileResponse(path, media_type=MESH_MEDIA[ext], filename=f"foot_{profile.side}.{ext}")


@router.get("/{profile_id}/last-spec")
def get_last_spec(profile_id: str, shoe: str | None = None, db: Session = Depends(get_session)) -> dict:
    """Custom last specification, optionally restricted to a shoe model's last family."""
    profile = _load(db, profile_id)
    family = None
    if shoe:
        model = get_shoe(shoe)
        if model is None:
            raise HTTPException(404, "shoe model not found")
        family = model.get("last_family")
    return {"profile_id": profile.id, "side": profile.side, "shoe": shoe, **build_last_spec(_measurements(profile), family)}
