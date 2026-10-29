import { Link } from 'react-router-dom';
import type { ScanWarning } from '../../lib/types';

const SIDE: Record<string, string> = { left: 'Left foot', right: 'Right foot', both: 'Both feet' };

/** Scan problems in plain language: what went wrong and what to do about it. */
export function WarningList({ warnings, retake = true }: { warnings: ScanWarning[]; retake?: boolean }) {
  if (!warnings.length) return null;
  const blocking = warnings.some((w) => w.severity === 'block');
  return (
    <div className="stack">
      {warnings.map((w, i) => (
        <div key={`${w.code}-${w.side ?? ''}-${i}`} className={`alert ${w.severity === 'block' ? 'error' : 'warning'} scan-warning`}>
          <div className="row between">
            <strong>{w.message}</strong>
            {w.side && <span className="pill">{SIDE[w.side] ?? w.side}</span>}
          </div>
          <div>{w.fix}</div>
        </div>
      ))}
      {retake && (
        <Link className={`btn ${blocking ? 'primary' : 'ghost'}`} to="/scan">Retake scan</Link>
      )}
    </div>
  );
}
