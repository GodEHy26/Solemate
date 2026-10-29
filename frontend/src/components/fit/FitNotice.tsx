import type { FitCheck } from '../../lib/types';
import { SizeDisplay } from './SizeDisplay';
import { WarningList } from './WarningList';

export function FitNotice({ fit }: { fit: FitCheck }) {
  return (
    <div className="card surface stack">
      <div className="row between">
        <strong>Your scans</strong>
        <span className={`pill ${fit.confidence === 'high' ? 'success' : fit.confidence === 'medium' ? 'warning' : 'error'}`}>
          {fit.confidence} confidence
        </span>
      </div>
      <SizeDisplay size={fit.size} />
      <WarningList warnings={fit.warnings} />
    </div>
  );
}
