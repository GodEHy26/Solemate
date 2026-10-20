import type { Measurements, Sizing } from '../../lib/types';

const ROWS: Array<[keyof Measurements, string]> = [
  ['length_mm', 'Foot length'],
  ['ball_width_mm', 'Ball width'],
  ['heel_width_mm', 'Heel width'],
  ['waist_width_mm', 'Waist width'],
  ['toe_width_mm', 'Toe width'],
  ['instep_height_mm', 'Instep height'],
  ['toe_height_mm', 'Toe height'],
  ['ball_girth_mm', 'Ball girth'],
  ['waist_girth_mm', 'Waist girth'],
  ['instep_girth_mm', 'Instep girth'],
];

export function MeasurementTable({ m }: { m: Measurements }) {
  return (
    <table className="measure">
      <tbody>
        {ROWS.map(([key, label]) => (
          <tr key={key}>
            <td className="muted">{label}</td>
            <td>{m[key] == null ? '—' : `${(m[key] as number).toFixed(1)} mm`}</td>
          </tr>
        ))}
        <tr>
          <td className="muted">Volume</td>
          <td>{m.volume_cm3.toFixed(0)} cm³</td>
        </tr>
      </tbody>
    </table>
  );
}

export function SizingCards({ s }: { s: Sizing }) {
  const r = s.recommended;
  return (
    <div className="stack">
      <div className="size-grid">
        <div className="size-tile"><div className="v">{r.us_men}</div><div className="k">US men</div></div>
        <div className="size-tile"><div className="v">{r.us_women}</div><div className="k">US women</div></div>
        <div className="size-tile"><div className="v">{r.eu}</div><div className="k">EU</div></div>
        <div className="size-tile"><div className="v">{r.uk}</div><div className="k">UK</div></div>
        <div className="size-tile"><div className="v">{s.width.code}</div><div className="k">{s.width.label}</div></div>
      </div>
      <p className="small muted">{s.notes.join(' ')}</p>
    </div>
  );
}
