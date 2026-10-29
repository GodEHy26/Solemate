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
from ..services.fitting.fit_check import pair_check, size_summary
from ..services.fitting.last_matcher import build_last_spec
from ..services.scanning.quality import ScanWarning
from ..services.scanning.quality import confidence as confidence_of
from ..services.retention import profile_in_open_order
from ..services.scanning.pipeline import delete_profile_data
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


def profile_warnings(profile: FootProfile) -> list[ScanWarning]:
    return [ScanWarning.from_dict(w) for w in json.loads(profile.warnings_json or "[]")]


def foot_assessment(profile: FootProfile) -> dict:
    m = json.loads(profile.measurements_json)
    return {"length_mm": m["length_mm"], "ball_width_mm": m["ball_width_mm"], "warnings": profile_warnings(profile)}


def to_out(profile: FootProfile) -> ProfileOut:
    profiles = json.loads(profile.profiles_json or "{}")
    warnings = profile_warnings(profile)
    m = json.loads(profile.measurements_json)
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
        warnings=[w.to_dict() for w in warnings],
        confidence=confidence_of(warnings),
        size=size_summary(m["length_mm"], m["ball_width_mm"], warnings),
        mesh_urls={ext: f"/api/profiles/{profile.id}/mesh.{ext}" for ext in MESH_MEDIA},
        created_at=profile.created_at,
    )


@router.get("/fit-check")
def fit_check(left: str, right: str, db: Session = Depends(get_session)) -> dict:
    """Both feet together: every warning, the left/right comparison, and the size to show."""
    return pair_check(foot_assessment(_load(db, left)), foot_assessment(_load(db, right)))


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


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_session)) -> None:
    """Delete a foot profile (measurements, 3D model, scan record). Blocked while a preorder uses it."""
    profile = _load(db, profile_id)
    if profile_in_open_order(db, profile.id):
        raise HTTPException(
            409,
            "This scan is attached to an open preorder, so we need it to make your shoes. "
            "Cancel the preorder first (email us) and then delete the scan.",
        )
    delete_profile_data(db, profile)
