import type { SizeSummary } from '../../lib/types';

const LABELS: Array<[keyof NonNullable<SizeSummary['sizes']>, string]> = [
  ['us_men', 'US men'],
  ['us_women', 'US women'],
  ['eu', 'EU'],
  ['uk', 'UK'],
];

const fmt = (r: { low: number; high: number }) => (r.low === r.high ? `${r.low}` : `${r.low} to ${r.high}`);

/** One size, a range when the scan has warnings, or nothing when a check blocks it. */
export function SizeDisplay({ size }: { size: SizeSummary }) {
  if (size.mode === 'none' || !size.sizes) {
    return (
      <div className="alert error">
        <strong>No size from this scan.</strong> {size.explanation}
      </div>
    );
  }
  return (
    <div className="stack">
      <div className={`size-grid${size.mode === 'range' ? ' range' : ''}`}>
        {LABELS.map(([k, label]) => (
          <div key={k} className="size-tile">
            <div className="v">{fmt(size.sizes![k])}</div>
            <div className="k">{label}</div>
          </div>
        ))}
        {size.width && (
          <div className="size-tile"><div className="v">{size.width.code}</div><div className="k">{size.width.label}</div></div>
        )}
      </div>
      <p className={`small ${size.mode === 'range' ? '' : 'muted'}`}>{size.explanation} Sizes are a guide; your pair is built on your scanned last.</p>
    </div>
  );
}
