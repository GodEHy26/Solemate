// Face-ID style progress ring: one arc per sector, filled as the sweep covers it.
interface Props {
  covered: boolean[];
  current: number | null;
  target: number | null;
  size?: number;
}

function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number): string {
  const toXY = (deg: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
  };
  const [x1, y1] = toXY(startDeg);
  const [x2, y2] = toXY(endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

export function CaptureRing({ covered, current, target, size = 400 }: Props) {
  const n = covered.length;
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.46;
  const sweep = 360 / n;
  const gap = Math.min(3, sweep * 0.25);
  return (
    <svg viewBox={`0 0 ${size} ${size}`} aria-label="scan coverage ring" role="img">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={size * 0.02} />
      {covered.map((on, i) => {
        const start = i * sweep + gap / 2;
        const end = (i + 1) * sweep - gap / 2;
        const isCurrent = current === i;
        const isTarget = target === i && !on;
        const stroke = on ? 'var(--success)' : isCurrent ? 'var(--accent)' : isTarget ? 'var(--warning)' : 'rgba(255,255,255,0.18)';
        return (
          <path
            key={i}
            d={arcPath(cx, cy, r, start, end)}
            fill="none"
            stroke={stroke}
            strokeWidth={size * (on || isCurrent ? 0.03 : 0.02)}
            strokeLinecap="round"
            className={isTarget ? 'pulse' : undefined}
          />
        );
      })}
    </svg>
  );
}
