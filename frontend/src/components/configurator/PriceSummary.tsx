import { formatPrice } from '../../lib/api';
import type { PriceResult } from '../../lib/types';

interface Props {
  price: PriceResult | null;
  pending: boolean;
  feetReady: boolean;
  onAdd: () => void;
}

export function PriceSummary({ price, pending, feetReady, onAdd }: Props) {
  if (!price) return <div className="card"><div className="spinner" /></div>;
  const blocked = !price.valid || (price.requires_scan && !feetReady);
  return (
    <div className="card stack sticky">
      <h3>Your build</h3>
      <div className="price-lines">
        <div><span>Base</span><span>{formatPrice(price.base_cents, price.currency)}</span></div>
        {price.lines.filter((l) => l.cents !== 0).map((l) => (
          <div key={l.component_id}><span>{l.option_name}</span><span>+ {formatPrice(l.cents, price.currency)}</span></div>
        ))}
        <div className="total"><span>Total</span><span>{pending ? '…' : formatPrice(price.total_cents, price.currency)}</span></div>
      </div>
      {price.errors.map((e) => <div key={e} className="alert error">{e}</div>)}
      {price.requires_scan && !feetReady && (
        <div className="alert warning">This build uses your 3D scan. <a href="/scan">Scan both feet</a> before adding it to the cart.</div>
      )}
      <button className="btn primary block lg" disabled={blocked || pending} onClick={onAdd}>Add to cart</button>
      <p className="small muted">Prices are confirmed by the server when you order. Shipping and tax are added at payment.</p>
    </div>
  );
}
