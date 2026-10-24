import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, apiUrl } from '../lib/api';
import type { FootProfile, ShoeSummary } from '../lib/types';
import { FootprintChart, SectionChart } from '../components/viewer/FootprintChart';
import { FootMeshViewer } from '../components/viewer/FootMeshViewer';
import { MeasurementTable, SizingCards } from '../components/viewer/MeasurementTable';
import { useFeet } from '../store/useFeet';

export function ProfilePage() {
  const { id = '' } = useParams();
  const [profile, setProfile] = useState<FootProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shoes, setShoes] = useState<ShoeSummary[]>([]);
  const [shoe, setShoe] = useState<string>('');
  const [lastSpec, setLastSpec] = useState<Record<string, unknown> | null>(null);
  const feet = useFeet((s) => s.profiles);
  const setFoot = useFeet((s) => s.setProfile);
  const clearFeet = useFeet((s) => s.clear);
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const deleteScan = async () => {
    if (!window.confirm('Delete this 3D scan and its measurements? This cannot be undone.')) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteProfile(id);
      const rest = Object.entries(feet).filter(([, v]) => v !== id);
      clearFeet();
      rest.forEach(([side, v]) => setFoot(side as 'left' | 'right', v as string));
      navigate('/scan');
    } catch (e) {
      setDeleteError((e as Error).message);
      setDeleting(false);
    }
  };

  useEffect(() => {
    api.getProfile(id).then((p) => {
      setProfile(p);
      if (feet[p.side] !== p.id) setFoot(p.side, p.id);
    }).catch((e: Error) => setError(e.message));
    api.listShoes().then(setShoes).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!profile) return;
    api.getLastSpec(profile.id, shoe || undefined).then(setLastSpec).catch(() => setLastSpec(null));
  }, [profile, shoe]);

  if (error) return <div className="container"><div className="alert error">{error}</div></div>;
  if (!profile) return <div className="container"><div className="spinner" /></div>;

  const m = profile.measurements;
  const other = profile.side === 'left' ? 'right' : 'left';
  const confidence = profile.scale_confidence;
  const spec = lastSpec as null | {
    base_last?: { name: string; family: string };
    graded_size_us?: number;
    adjustments_mm?: Record<string, number>;
  };

  return (
    <div className="container stack">
      <div className="row between">
        <div>
          <h1>Your {profile.side} foot</h1>
          <p className="small">
            {profile.source === 'uploaded_mesh' ? 'From an uploaded depth-sensor mesh' : 'Reconstructed from your photo sweep'} ·
            scale from <code>{profile.scale_method}</code>
          </p>
        </div>
        <span className={`pill ${confidence === 'high' ? 'success' : confidence === 'medium' ? 'warning' : 'error'}`}>
          scale confidence: {confidence}
        </span>
      </div>

      {profile.warnings.length > 0 && (
        <div className="alert warning">{profile.warnings.join(' ')}</div>
      )}

      <div className="grid two">
        <div className="stack">
          <FootMeshViewer url={apiUrl(profile.mesh_urls.glb)} />
          <div className="row">
            <a className="btn ghost" href={apiUrl(profile.mesh_urls.glb)} download>Download GLB</a>
            <a className="btn ghost" href={apiUrl(profile.mesh_urls.obj)} download>Download OBJ</a>
          </div>
          <div className="card">
            <h3 className="mb">Footprint contour</h3>
            <FootprintChart profile={profile} />
          </div>
          {profile.sections.length > 0 && (
            <div className="card">
              <h3 className="mb">Cross-sections</h3>
              <div className="grid">
                {profile.sections.map((s) => (
                  <div key={s.name}>
                    <SectionChart points={s.points} label={`${s.name} · ${s.girth_mm?.toFixed(0) ?? '—'} mm girth`} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="stack">
          <div className="card">
            <h3 className="mb">Measurements</h3>
            <MeasurementTable m={m} />
          </div>
          <div className="card">
            <h3 className="mb">Size guide</h3>
            <SizingCards s={profile.sizing} />
          </div>
          <div className="card stack">
            <h3>Custom last</h3>
            <label className="field">
              For shoe model
              <select value={shoe} onChange={(e) => setShoe(e.target.value)}>
                <option value="">Any last family</option>
                {shoes.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
              </select>
            </label>
            {spec?.base_last ? (
              <div className="small">
                <div>Base last: <strong>{spec.base_last.name}</strong> ({spec.base_last.family})</div>
                <div>Graded to US {spec.graded_size_us}, then adjusted:</div>
                <ul style={{ margin: '6px 0 0 18px', color: 'var(--text-2)' }}>
                  {Object.entries(spec.adjustments_mm ?? {}).map(([k, v]) => (
                    <li key={k}>{k.replace('_mm', '').replace('_', ' ')}: {v > 0 ? '+' : ''}{v.toFixed(1)} mm</li>
                  ))}
                </ul>
              </div>
            ) : <p className="small muted">Computing last specification…</p>}
          </div>
          <div className="row">
            {!feet[other] && <Link className="btn primary" to="/scan">Scan {other} foot</Link>}
            <Link className="btn ghost" to="/shoes">Preorder shoes</Link>
          </div>
          <div className="card stack">
            <h3>Your data</h3>
            <p className="small">Your photos were already deleted when this model was built. You can delete the model and measurements too. See the <Link to="/privacy">Privacy Policy</Link>.</p>
            {deleteError && <div className="alert error">{deleteError}</div>}
            <button className="btn danger" onClick={deleteScan} disabled={deleting}>{deleting ? 'Deleting…' : 'Delete this scan'}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
