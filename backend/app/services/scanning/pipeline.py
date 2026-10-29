
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from sqlmodel import Session

from ...config import get_settings
from ...database import get_engine
from ...db_models import FootProfile, ScanSession
from ..fitting.last_matcher import build_last_spec
from .meshing import export_mesh
from .reconstructor import (
    FrameInput,
    ReconstructionError,
    ScanResult,
    UploadedMeshReconstructor,
    VisualHullReconstructor,
)
from .sizing import recommend_sizing

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_MESH_SUFFIXES = {".glb", ".gltf", ".obj", ".ply", ".stl"}


def session_dir(session_id: str) -> Path:
    d = get_settings().scans_dir / session_id
    (d / "frames").mkdir(parents=True, exist_ok=True)
    return d


def delete_session_files(session_id: str) -> None:
    shutil.rmtree(get_settings().scans_dir / session_id, ignore_errors=True)


def save_frame(session_id: str, index: int, kind: str, data: bytes) -> Path:

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("file is not a decodable image")
    path = session_dir(session_id) / "frames" / f"{index:03d}_{kind}.jpg"
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return path


def save_mesh_upload(session_id: str, filename: str, data: bytes) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_MESH_SUFFIXES:
        raise ValueError(f"unsupported mesh format {suffix}; use one of {sorted(ALLOWED_MESH_SUFFIXES)}")
    path = session_dir(session_id) / f"upload{suffix}"
    path.write_bytes(data)
    return path


def discard_raw_inputs(session_id: str) -> None:

    d = get_settings().scans_dir / session_id
    shutil.rmtree(d / "frames", ignore_errors=True)
    for f in d.glob("upload.*"):
        f.unlink(missing_ok=True)


def delete_profile_data(db: Session, profile: FootProfile) -> None:

    session = db.get(ScanSession, profile.scan_session_id)
    delete_session_files(profile.scan_session_id)
    db.delete(profile)
    if session is not None:
        db.delete(session)
    db.commit()


def frames_from_session(session: ScanSession) -> list[FrameInput]:
    return [
        FrameInput(path=Path(f["path"]), kind=f["kind"], yaw_deg=f["yaw_deg"], pitch_deg=f["pitch_deg"], index=f["index"])
        for f in json.loads(session.frames_json)
    ]


def _persist_result(db: Session, session: ScanSession, result: ScanResult) -> FootProfile:
    out_dir = session_dir(session.id)
    glb = export_mesh(result.mesh, out_dir / "foot.glb")
    obj = export_mesh(result.mesh, out_dir / "foot.obj")
    m = result.geometry.measurements
    profile = FootProfile(
        scan_session_id=session.id,
        side=session.side,
        source=result.source,
        scale_method=result.scale_method,
        scale_confidence=result.scale_confidence,
        measurements_json=json.dumps(m.as_dict()),
        sizing_json=json.dumps(recommend_sizing(m.length_mm, m.ball_width_mm)),
        footprint_json=json.dumps(result.geometry.footprint_mm),
        profiles_json=json.dumps(
            {"width": result.geometry.width_profile, "height": result.geometry.height_profile, "topdown": result.topdown}
        ),
        sections_json=json.dumps(result.geometry.sections),
        warnings_json=json.dumps([w.to_dict() for w in result.warnings]),
        confidence=result.confidence,
        mesh_glb_path=str(glb),
        mesh_obj_path=str(obj),
    )
    db.add(profile)
    db.flush()
    (out_dir / "profile.json").write_text(
        json.dumps(
            {
                "profile_id": profile.id,
                "side": session.side,
                "measurements": m.as_dict(),
                "sizing": json.loads(profile.sizing_json),
                "last_spec": build_last_spec(m),
                "scale": {"method": result.scale_method, "confidence": result.scale_confidence, "factor": result.scale_factor},
                "warnings": [w.to_dict() for w in result.warnings],
                "confidence": result.confidence,
                "notes": result.notes,
            },
            indent=2,
        )
    )
    session.status = "complete"
    session.profile_id = profile.id
    session.error = None
    session.warnings_json = json.dumps([w.to_dict() for w in result.warnings])
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    return profile


def process_session(session_id: str) -> None:

    with Session(get_engine()) as db:
        session = db.get(ScanSession, session_id)
        if session is None:
            return
        try:
            result = VisualHullReconstructor().reconstruct(
                frames_from_session(session),
                known_length_mm=session.known_length_mm,
                paper=session.paper_size,
            )
            _persist_result(db, session, result)
            db.commit()
            discard_raw_inputs(session.id)
            return
        except (ReconstructionError, ValueError) as exc:
            session.status = "failed"
            session.error = str(exc)
            session.warnings_json = json.dumps([w.to_dict() for w in getattr(exc, "warnings", [])])
            session.updated_at = datetime.now(timezone.utc)
            db.add(session)
        db.commit()


def process_uploaded_mesh(session_id: str, mesh_path: Path, units: str) -> None:
    with Session(get_engine()) as db:
        session = db.get(ScanSession, session_id)
        if session is None:
            return
        try:
            result = UploadedMeshReconstructor().reconstruct(mesh_path, units)
            _persist_result(db, session, result)
            db.commit()
            discard_raw_inputs(session.id)
            return
        except (ReconstructionError, ValueError) as exc:
            session.status = "failed"
            session.error = str(exc)
            session.updated_at = datetime.now(timezone.utc)
            db.add(session)
        db.commit()
