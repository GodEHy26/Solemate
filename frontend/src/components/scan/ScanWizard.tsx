import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError, waitForScan } from '../../lib/api';
import { useCamera } from '../../lib/hooks/useCamera';
import { useDeviceOrientation } from '../../lib/hooks/useOrientation';
import {
  coverageFraction,
  createRing,
  isComplete,
  largestGapDeg,
  manualAdvance,
  markCovered,
  nextTargetSector,
  relativeYaw,
  sectorOf,
  shouldCapture,
  startSweep,
  type RingState,
} from '../../lib/scanSession';
import type { CapturePlan, ScanWarning, Side } from '../../lib/types';
import { WarningList } from '../fit/WarningList';
import { useFeet } from '../../store/useFeet';
import { CaptureRing } from './CaptureRing';

type Step = 'intro' | 'topdown' | 'orbit' | 'processing' | 'failed';

export function ScanWizard() {
  const navigate = useNavigate();
  const setProfile = useFeet((s) => s.setProfile);

  const [plan, setPlan] = useState<CapturePlan | null>(null);
  const [step, setStep] = useState<Step>('intro');
  const [side, setSide] = useState<Side>('left');
  const [paper, setPaper] = useState('A4');
  const [knownLength, setKnownLength] = useState('');
  const [scanId, setScanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failWarnings, setFailWarnings] = useState<ScanWarning[]>([]);
  const [status, setStatus] = useState<string>('');
  const [ring, setRing] = useState<RingState>(() => createRing(15));
  const [mode, setMode] = useState<'auto' | 'manual'>('manual');
  const [thumbs, setThumbs] = useState<string[]>([]);
  const [uploading, setUploading] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const ringRef = useRef(ring);
  ringRef.current = ring;
  const pending = useRef<Promise<unknown>[]>([]);

  const cameraActive = step === 'topdown' || step === 'orbit';
  const insecure = typeof window !== 'undefined' && !window.isSecureContext;

  useEffect(() => {
    if (!(step === 'topdown' || step === 'orbit')) return;
    type WakeNav = Navigator & { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } };
    let lock: { release: () => Promise<void> } | null = null;
    (navigator as WakeNav).wakeLock?.request('screen').then((l) => { lock = l; }).catch(() => undefined);
    return () => { void lock?.release(); };
  }, [step]);
  const camera = useCamera(cameraActive);
  const orientation = useDeviceOrientation(step === 'orbit');

  useEffect(() => {
    api.capturePlan().then((p) => {
      setPlan(p);
      setRing(createRing(p.sector_deg));
    }).catch((e: Error) => setError(`API unreachable: ${e.message}`));
  }, []);

  useEffect(() => {
    if (orientation.status === 'active' && mode !== 'auto') setMode('auto');
  }, [orientation.status, mode]);

  const upload = useCallback(
    (blob: Blob, meta: { yaw_deg: number; pitch_deg: number; kind: 'orbit' | 'topdown' }) => {
      if (!scanId) return;
      setUploading((n) => n + 1);
      const p = api
        .uploadFrame(scanId, blob, meta)
        .then((s) => setFrameCount(s.frame_count))
        .catch((e: Error) => setError(e.message))
        .finally(() => setUploading((n) => n - 1));
      pending.current.push(p);
      setThumbs((t) => [...t.slice(-11), URL.createObjectURL(blob)]);
    },
    [scanId],
  );

  const begin = async () => {
    setError(null);
    try {
      const s = await api.createScan(side, {
        paper_size: paper,
        known_length_mm: knownLength ? Number(knownLength) : undefined,
      });
      setScanId(s.id);
      setThumbs([]);
      setFrameCount(0);
      setRing(createRing(plan?.sector_deg ?? 15));
      setStep('topdown');
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const captureTopdown = async () => {
    const blob = await camera.snapshot();
    if (!blob) return setError('Camera frame not ready yet.');
    upload(blob, { yaw_deg: 0, pitch_deg: 90, kind: 'topdown' });
    setStep('orbit');
  };

  const skipTopdown = () => setStep('orbit');

  const currentSector = useMemo(() => {
    if (orientation.yaw === null) return null;
    const rel = relativeYaw(ring, orientation.yaw);
    return rel === null ? null : sectorOf(rel, ring.sectorDeg);
  }, [orientation.yaw, ring]);

  useEffect(() => {
    if (step !== 'orbit' || mode !== 'auto' || camera.status !== 'ready') return;
    const id = window.setInterval(async () => {
      const r = ringRef.current;
      if (r.yawOffset === null) return;
      const decision = shouldCapture(r, orientation.yaw, orientation.jitter, Date.now());
      if (!decision.capture || decision.sector === null) return;
      const blob = await camera.snapshot(960);
      if (!blob) return;
      const rel = relativeYaw(r, orientation.yaw!)!;
      const next = markCovered(r, decision.sector, Date.now());
      ringRef.current = next;
      setRing(next);
      upload(blob, { yaw_deg: rel, pitch_deg: plan?.orbit_pitch_deg ?? 30, kind: 'orbit' });
    }, 250);
    return () => window.clearInterval(id);
  }, [step, mode, camera, orientation.yaw, orientation.jitter, plan, upload]);

  const startAuto = () => {
    if (orientation.yaw === null) return;
    setRing((r) => startSweep(r, orientation.yaw!));
  };

  const manualCapture = async () => {
    const blob = await camera.snapshot(960);
    if (!blob) return setError('Camera frame not ready yet.');
    const { ring: next, sector } = manualAdvance(ringRef.current, Date.now());
    if (sector === null) return;
    ringRef.current = next;
    setRing(next);
    upload(blob, { yaw_deg: sector * next.sectorDeg, pitch_deg: plan?.orbit_pitch_deg ?? 30, kind: 'orbit' });
  };

  const finish = async () => {
    if (!scanId) return;
    setStep('processing');
    setStatus('Uploading the last frames…');
    await Promise.allSettled(pending.current);
    try {
      setStatus('Building the 3D model…');
      await api.reconstruct(scanId);
      const done = await waitForScan(scanId, (s) => setStatus(`Status: ${s.status}…`));
      if (done.status === 'complete' && done.profile_id) {
        setProfile(side, done.profile_id);
        navigate(`/profiles/${done.profile_id}`);
      } else {
        setFailWarnings(done.warnings ?? []);
        setError(done.warnings?.length ? null : done.error ?? 'Reconstruction failed.');
        setStep('failed');
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : (e as Error).message);
      setStep('failed');
    }
  };

  const uploadMeshFile = async (file: File) => {
    setError(null);
    try {
      const s = await api.createScan(side, {});
      setScanId(s.id);
      setStep('processing');
      setStatus('Uploading mesh…');
      await api.uploadMesh(s.id, file, 'mm');
      const done = await waitForScan(s.id, (st) => setStatus(`Status: ${st.status}…`));
      if (done.status === 'complete' && done.profile_id) {
        setProfile(side, done.profile_id);
        navigate(`/profiles/${done.profile_id}`);
      } else {
        setFailWarnings(done.warnings ?? []);
        setError(done.error ?? 'Could not measure that mesh.');
        setStep('failed');
      }
    } catch (e) {
      setError((e as Error).message);
      setStep('failed');
    }
  };

  const coverage = coverageFraction(ring);
  const complete = isComplete(ring);
  const minFrames = plan?.min_orbit_frames ?? 8;
  const orbitFrames = ring.covered.filter(Boolean).length;
  const target = nextTargetSector(ring, currentSector);

  return (
    <div className="container narrow stack">
      <div className="row between">
        <h1>Scan your {side} foot</h1>
        <span className="pill">{step}</span>
      </div>
      {error && <div className="alert error">{error}</div>}
      {insecure && (
        <div className="alert warning">
          This page is not on HTTPS, so your phone will block the camera and motion sensors. Open the site over
          https:// (see docs/DEPLOYMENT.md for a quick tunnel).
        </div>
      )}

      {step === 'intro' && (
        <div className="card stack">
          <div className="row between">
            <strong>Which foot?</strong>
            <div className="segmented">
              <button className={side === 'left' ? 'on' : ''} onClick={() => setSide('left')}>Left</button>
              <button className={side === 'right' ? 'on' : ''} onClick={() => setSide('right')}>Right</button>
            </div>
          </div>
          <div className="grid">
            <label className="field">
              Paper under your foot (scale reference)
              <select value={paper} onChange={(e) => setPaper(e.target.value)}>
                {(plan?.paper_sizes ?? ['A4', 'LETTER']).map((p) => <option key={p}>{p}</option>)}
              </select>
            </label>
            <label className="field">
              Known foot length in mm (optional fallback)
              <input type="number" inputMode="decimal" min={150} max={380} value={knownLength} onChange={(e) => setKnownLength(e.target.value)} placeholder="e.g. 265" />
            </label>
          </div>
          <div className="alert">
            Stand barefoot on a plain floor with the sheet of paper under your foot. Good, even light and a floor
            that contrasts with your skin give the cleanest result. Keep your lower leg still during the sweep.
          </div>
          <p className="small muted">
            Your photos are used only to build your 3D model and are deleted from our server as soon as it is built.
            You can delete the model any time. See the <Link to="/privacy">Privacy Policy</Link>.
          </p>
          <button className="btn primary lg" onClick={begin} disabled={!plan}>Start scan</button>
          <details>
            <summary className="muted small">Have a mesh from a LiDAR / TrueDepth app? Upload it instead.</summary>
            <input className="mt" type="file" accept=".glb,.gltf,.obj,.ply,.stl" onChange={(e) => e.target.files?.[0] && uploadMeshFile(e.target.files[0])} />
          </details>
        </div>
      )}

      {step === 'topdown' && (
        <div className="card stack">
          <strong>Step 1 · Top-down photo</strong>
          <p className="small">Hold the phone flat above your foot so the whole sheet of paper is inside the dashed frame.</p>
          <div className="scan-stage">
            <video ref={camera.videoRef} className="square" playsInline muted autoPlay />
            <div className="paper-guide" />
            {camera.status !== 'ready' && <div className="overlay-msg">{cameraMessage(camera.status)}</div>}
          </div>
          <div className="scan-hud">
            <button className="btn primary" onClick={captureTopdown} disabled={camera.status !== 'ready'}>Capture</button>
            <button className="btn ghost" onClick={skipTopdown}>Skip (no size without the paper)</button>
          </div>
        </div>
      )}

      {step === 'orbit' && (
        <div className="card stack">
          <div className="row between">
            <strong>Step 2 · Orbit sweep</strong>
            <span className="pill">{Math.round(coverage * 100)}% · {orbitFrames} frames{uploading > 0 ? ` · uploading ${uploading}` : ''}</span>
          </div>
          <div className="scan-stage">
            <video ref={camera.videoRef} playsInline muted autoPlay />
            <CaptureRing covered={ring.covered} current={currentSector} target={target} />
            {camera.status !== 'ready' && <div className="overlay-msg">{cameraMessage(camera.status)}</div>}
          </div>
          <div className="progress"><div style={{ width: `${coverage * 100}%` }} /></div>

          {mode === 'auto' ? (
            ring.yawOffset === null ? (
              <div className="stack">
                <p className="small">Motion sensors detected. Point the camera at your toes from about 45 cm away, then start the sweep and walk slowly around the foot.</p>
                <button className="btn primary" onClick={startAuto} disabled={orientation.yaw === null || camera.status !== 'ready'}>Start sweep</button>
              </div>
            ) : (
              <p className="small">
                {complete ? 'Coverage complete. You can keep going for extra detail or finish.' : hint(target, currentSector, ring)}
                {orientation.jitter > 6 && ' Hold steadier.'}
              </p>
            )
          ) : (
            <div className="stack">
              {orientation.status === 'needs-permission' && (
                <button className="btn ghost" onClick={() => orientation.request()}>Enable motion sensors for automatic capture</button>
              )}
              <p className="small">
                Manual mode: start in front of your toes, then move about {ring.sectorDeg}° counter-clockwise (seen from above) between taps, keeping the foot centred in the ring.
                {' '}Next: {target !== null ? `${target * ring.sectorDeg}°` : 'done'}.
              </p>
              <button className="btn primary" onClick={manualCapture} disabled={camera.status !== 'ready' || target === null}>Capture frame</button>
            </div>
          )}

          {thumbs.length > 0 && <div className="thumbs">{thumbs.map((t) => <img key={t} src={t} alt="" />)}</div>}
          <button className="btn primary lg" onClick={finish} disabled={orbitFrames < minFrames || uploading > 0}>
            {complete ? 'Build 3D model' : orbitFrames < minFrames ? `Need ${minFrames - orbitFrames} more frames` : `Build anyway (gap ${largestGapDeg(ring)}°)`}
          </button>
          <p className="small muted">Frames on server: {frameCount}</p>
        </div>
      )}

      {step === 'processing' && (
        <div className="card stack" style={{ alignItems: 'center', textAlign: 'center' }}>
          <div className="spinner" />
          <strong>Reconstructing your foot</strong>
          <p className="small">{status}</p>
          <p className="small muted">Silhouettes → visual hull → mesh → measurements. Usually 10–30 seconds.</p>
        </div>
      )}

      {step === 'failed' && (
        <div className="card stack">
          <strong>That scan did not work</strong>
          {failWarnings.length > 0 ? (
            <WarningList warnings={failWarnings} />
          ) : (
            <p className="small">Try again with a plainer floor, more light, and the whole foot inside the ring in every frame.</p>
          )}
          <button className="btn primary" onClick={() => { setStep('intro'); setError(null); setFailWarnings([]); }}>Start over</button>
        </div>
      )}
    </div>
  );
}

function cameraMessage(status: string): string {
  switch (status) {
    case 'starting':
      return 'Starting camera…';
    case 'denied':
      return 'Camera permission was denied. Allow camera access and reload.';
    case 'unavailable':
      return 'No camera available on this device/browser.';
    default:
      return '';
  }
}

function hint(target: number | null, current: number | null, ring: RingState): string {
  if (target === null || current === null) return 'Keep the foot centred and move around it.';
  const diff = ((target - current) % ring.sectorCount + ring.sectorCount) % ring.sectorCount;
  if (diff === 0) return 'Hold still…';
  return diff <= ring.sectorCount / 2
    ? `Move counter-clockwise about ${diff * ring.sectorDeg}°.`
    : `Move clockwise about ${(ring.sectorCount - diff) * ring.sectorDeg}°.`;
}
