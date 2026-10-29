import { formatPrice } from '../../lib/api';
import type { ShoeComponent } from '../../lib/types';

interface Props {
  component: ShoeComponent;
  value: string | undefined;
  color: string | undefined;
  currency: string;
  onChange: (optionId: string) => void;
  onColor: (hex: string) => void;
}

export function ComponentPicker({ component, value, color, currency, onChange, onColor }: Props) {
  const selected = component.options.find((o) => o.id === value);
  return (
    <section className="card stack">
      <div>
        <h3>{component.name}</h3>
        <p className="small">{component.description}</p>
      </div>
      <div className="option-grid">
        {component.options.map((o) => {
          const props = Object.entries(o.properties ?? {}).slice(0, 4);
          return (
            <button key={o.id} type="button" className={`option${o.id === value ? ' on' : ''}`} onClick={() => onChange(o.id)}>
              <span className="name">{o.name}</span>
              <span className="mat">{o.material}</span>
              <span className="delta">{o.price_delta_cents === 0 ? 'Included' : `+ ${formatPrice(o.price_delta_cents, currency)}`}</span>
              {props.length > 0 && (
                <span className="props">
                  {props.map(([k, v]) => (
                    <span key={k} className="prop">
                      <span>{k.replace('_', ' ')}</span>
                      <span className="bar"><div style={{ width: `${(v / 5) * 100}%` }} /></span>
                    </span>
                  ))}
                </span>
              )}
              {o.requires_scan && <span className="pill accent">needs scan</span>}
            </button>
          );
        })}
      </div>
      {selected && selected.colors.length > 0 && (
        <div className="row">
          <span className="small muted">Colour</span>
          <div className="swatches">
            {selected.colors.map((c) => (
              <button key={c} type="button" aria-label={c} className={`swatch-dot${c === color ? ' on' : ''}`} style={{ background: c }} onClick={() => onColor(c)} />
            ))}
          </div>
        </div>
      )}
      {selected?.notes && <p className="small muted">{selected.notes}</p>}
    </section>
  );
}
