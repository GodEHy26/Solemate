
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from ..config import get_settings
from ..database import get_session
from ..db_models import ScanSession
from ..schemas import CoverageOut, FrameOut, ScanCreate, ScanOut
from ..services.scanning import capture_plan as cp
from ..services.scanning import pipeline

router = APIRouter(prefix="/api/scans", tags=["scans"])


def _coverage(frames: list[dict]) -> CoverageOut:
    s = get_settings()
    yaws = [f["yaw_deg"] for f in frames if f["kind"] == cp.ORBIT_KIND]
    return CoverageOut(
        fraction=round(cp.coverage_fraction(yaws, s.sector_deg), 3),
        missing_sectors=cp.missing_sectors(yaws, s.sector_deg),
        largest_gap_deg=round(cp.largest_gap_deg(yaws), 1),
        sector_count=cp.sector_count(s.sector_deg),
    )


def _to_out(session: ScanSession) -> ScanOut:
    frames = json.loads(session.frames_json)
    return ScanOut(
        id=session.id,
        side=session.side,
        status=session.status,
        frame_count=session.frame_count,
        frames=[FrameOut(index=f["index"], kind=f["kind"], yaw_deg=f["yaw_deg"], pitch_deg=f["pitch_deg"]) for f in frames],
        coverage=_coverage(frames),
        known_length_mm=session.known_length_mm,
        paper_size=session.paper_size,
        error=session.error,
        warnings=json.loads(session.warnings_json or "[]"),
        profile_id=session.profile_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _load(db: Session, scan_id: str) -> ScanSession:
    session = db.get(ScanSession, scan_id)
    if session is None:
        raise HTTPException(404, "scan session not found")
    return session


@router.get("/plan")
def get_plan() -> dict:

    s = get_settings()
    poses = cp.build_capture_plan(s.sector_deg, s.orbit_pitch_deg, include_topdown=True)
    return {
        "sector_deg": s.sector_deg,
        "sector_count": cp.sector_count(s.sector_deg),
        "orbit_pitch_deg": s.orbit_pitch_deg,
        "min_orbit_frames": s.min_orbit_frames,
        "paper_sizes": ["A4", "LETTER", "A3"],
        "poses": [p.to_dict() for p in poses],
    }


@router.post("", response_model=ScanOut, status_code=201)
def create_scan(payload: ScanCreate, db: Session = Depends(get_session)) -> ScanOut:
    session = ScanSession(
        side=payload.side,
        known_length_mm=payload.known_length_mm,
        paper_size=payload.paper_size or get_settings().paper_size,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    pipeline.session_dir(session.id)
    return _to_out(session)


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: str, db: Session = Depends(get_session)) -> ScanOut:
    return _to_out(_load(db, scan_id))


@router.post("/{scan_id}/frames", response_model=ScanOut, status_code=201)
async def upload_frame(
    scan_id: str,
    image: UploadFile = File(...),
    yaw_deg: float = Form(0.0),
    pitch_deg: float = Form(30.0),
    kind: str = Form(cp.ORBIT_KIND),
    db: Session = Depends(get_session),
) -> ScanOut:
    session = _load(db, scan_id)
    if session.status != "capturing":
        raise HTTPException(409, f"session is {session.status}; frames can only be added while capturing")
    if kind not in (cp.ORBIT_KIND, cp.TOPDOWN_KIND):
        raise HTTPException(422, "kind must be 'orbit' or 'topdown'")
    data = await image.read()
    if len(data) > 16 * 1024 * 1024:
        raise HTTPException(413, "frame larger than 16 MB")
    frames = json.loads(session.frames_json)
    index = len(frames)
    try:
        path = pipeline.save_frame(session.id, index, kind, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    frames.append({"index": index, "kind": kind, "yaw_deg": yaw_deg % 360.0, "pitch_deg": pitch_deg, "path": str(path)})
    session.frames_json = json.dumps(frames)
    session.frame_count = len(frames)
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_out(session)


@router.post("/{scan_id}/reconstruct", response_model=ScanOut, status_code=202)
def reconstruct(scan_id: str, background: BackgroundTasks, db: Session = Depends(get_session)) -> ScanOut:
    session = _load(db, scan_id)
    if session.status not in ("capturing", "failed"):
        raise HTTPException(409, f"session is already {session.status}")
    frames = json.loads(session.frames_json)
    orbit_yaws = [f["yaw_deg"] for f in frames if f["kind"] == cp.ORBIT_KIND]
    s = get_settings()
    if len(orbit_yaws) < s.min_orbit_frames:
        raise HTTPException(422, f"need at least {s.min_orbit_frames} orbit frames, have {len(orbit_yaws)}")
    ok, problems = cp.validate_coverage(orbit_yaws, s.sector_deg, min_fraction=0.5, max_gap_deg=120.0)
    if not ok:
        raise HTTPException(422, " ".join(problems))
    session.status = "processing"
    session.error = None
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    if s.sync_processing:
        pipeline.process_session(session.id)
        db.refresh(session)
    else:
        background.add_task(pipeline.process_session, session.id)
    return _to_out(session)


@router.post("/{scan_id}/mesh", response_model=ScanOut, status_code=202)
async def upload_mesh(
    scan_id: str,
    background: BackgroundTasks,
    mesh: UploadFile = File(...),
    units: str = Form("mm"),
    db: Session = Depends(get_session),
) -> ScanOut:

    session = _load(db, scan_id)
    if session.status not in ("capturing", "failed"):
        raise HTTPException(409, f"session is already {session.status}")
    data = await mesh.read()
    if len(data) > 64 * 1024 * 1024:
        raise HTTPException(413, "mesh larger than 64 MB")
    try:
        path = pipeline.save_mesh_upload(session.id, mesh.filename or "upload.glb", data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    session.status = "processing"
    session.updated_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    if get_settings().sync_processing:
        pipeline.process_uploaded_mesh(session.id, path, units)
        db.refresh(session)
    else:
        background.add_task(pipeline.process_uploaded_mesh, session.id, path, units)
    return _to_out(session)


@router.delete("/{scan_id}", status_code=204)
def delete_scan(scan_id: str, db: Session = Depends(get_session)) -> None:
    session = _load(db, scan_id)
    pipeline.delete_session_files(session.id)
    db.delete(session)
    db.commit()
