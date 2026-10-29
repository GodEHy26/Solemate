import { Link } from 'react-router-dom';
import { formatPrice } from '../../lib/api';
import { useFitCheck } from '../../lib/hooks/useFitCheck';
import { useSiteConfig } from '../../lib/hooks/useSiteConfig';
import { FitNotice } from '../fit/FitNotice';
import type { PriceResult } from '../../lib/types';

interface Props {
  price: PriceResult | null;
  pending: boolean;
  feetReady: boolean;
  onAdd: () => void;
}

export function PriceSummary({ price, pending, feetReady, onAdd }: Props) {
  const cfg = useSiteConfig();
  const { fit } = useFitCheck();
  if (!price) return <div className="card"><div className="spinner" /></div>;
  const blocked = !price.valid;
  return (
    <div className="card stack sticky">
      <div className="row between">
        <h3>Your preorder</h3>
        <span className="pill warning">Preorder</span>
      </div>
      <div className="price-lines">
        <div><span>Base</span><span>{formatPrice(price.base_cents, price.currency)}</span></div>
        {price.lines.filter((l) => l.cents !== 0).map((l) => (
          <div key={l.component_id}><span>{l.option_name}</span><span>+ {formatPrice(l.cents, price.currency)}</span></div>
        ))}
        <div className="total"><span>Total</span><span>{pending ? '…' : formatPrice(price.total_cents, price.currency)}</span></div>
      </div>
      {price.errors.map((e) => <div key={e} className="alert error">{e}</div>)}
      {!feetReady && (
        <div className="alert warning">Shoes are made from your scan. <Link to="/scan">Scan both feet</Link> before you check out.</div>
      )}
      {fit && <FitNotice fit={fit} />}
      <button className="btn primary block lg" disabled={blocked || pending} onClick={onAdd}>Add preorder to cart</button>
      <p className="small muted">{cfg?.ship_estimate} Paid in full at checkout. See the <Link to="/terms">Preorder Terms</Link>.</p>
    </div>
  );
}
