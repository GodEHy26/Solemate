import type { FootProfile } from '../../lib/types';

export function FootprintChart({ profile }: { profile: FootProfile }) {
  const pts = profile.footprint_mm;
  if (!pts.length) return <p className="small muted">No footprint available.</p>;
  const m = profile.measurements;
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const pad = 14;
  const minX = Math.min(...xs) - pad;
  const maxX = Math.max(...xs) + pad;
  const minY = Math.min(...ys) - pad;
  const maxY = Math.max(...ys) + pad;
  const w = maxX - minX;
  const h = maxY - minY;
  const stations = [
    { x: m.ball_position_mm, label: `ball ${m.ball_width_mm.toFixed(0)} mm` },
    { x: m.waist_position_mm, label: `waist ${m.waist_width_mm.toFixed(0)} mm` },
    { x: m.length_mm * 0.1, label: `heel ${m.heel_width_mm.toFixed(0)} mm` },
  ];
  return (
    <svg viewBox={`${minX} ${minY} ${w} ${h}`} style={{ width: '100%', maxHeight: 220 }} role="img" aria-label="footprint outline">
      <polygon points={pts.map((p) => `${p[0]},${p[1]}`).join(' ')} fill="rgba(40,171,255,0.15)" stroke="var(--accent)" strokeWidth={1.5} />
      {stations.map((s) => (
        <g key={s.label}>
          <line x1={s.x} x2={s.x} y1={minY + 4} y2={maxY - 4} stroke="rgba(255,255,255,0.25)" strokeDasharray="3 3" />
          <text x={s.x + 2} y={minY + 10} fill="var(--text-2)" fontSize={7}>{s.label}</text>
        </g>
      ))}
      <text x={minX + 4} y={maxY - 4} fill="var(--text-3)" fontSize={7}>heel</text>
      <text x={maxX - 18} y={maxY - 4} fill="var(--text-3)" fontSize={7}>toes</text>
      <text x={minX + 4} y={minY + h / 2} fill="var(--text-3)" fontSize={7}>{m.length_mm.toFixed(0)} mm</text>
    </svg>
  );
}

export function SectionChart({ points, label }: { points: [number, number][]; label: string }) {
  if (!points.length) return null;
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const pad = 6;
  const minX = Math.min(...xs) - pad;
  const maxX = Math.max(...xs) + pad;
  const minY = Math.min(...ys) - pad;
  const maxY = Math.max(...ys) + pad;
  return (
    <svg viewBox={`${minX} ${-maxY} ${maxX - minX} ${maxY - minY}`} style={{ width: '100%', maxHeight: 120 }} role="img" aria-label={`${label} cross-section`}>
      <polygon points={points.map((p) => `${p[0]},${-p[1]}`).join(' ')} fill="rgba(60,207,142,0.12)" stroke="var(--success)" strokeWidth={1} />
      <text x={minX + 2} y={-minY - 2} fill="var(--text-3)" fontSize={6}>{label}</text>
    </svg>
  );
}
