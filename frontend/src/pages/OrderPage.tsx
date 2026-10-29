import { useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api, formatPrice } from '../lib/api';
import type { OrderOut } from '../lib/types';
import { useCart } from '../store/useCart';

const STATUS: Record<string, { label: string; tone: string }> = {
  preordered: { label: 'Preorder confirmed', tone: 'success' },
  awaiting_payment: { label: 'Awaiting payment', tone: 'warning' },
  payment_failed: { label: 'Payment failed', tone: 'error' },
  needs_review: { label: 'Payment under review', tone: 'warning' },
  cancelled: { label: 'Cancelled', tone: 'error' },
};

export function OrderPage() {
  const { id = '' } = useParams();
  const [params] = useSearchParams();
  const returningFromStripe = params.get('paid') === '1';
  const clearCart = useCart((s) => s.clear);
  const [order, setOrder] = useState<OrderOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(returningFromStripe);
  const tries = useRef(0);

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const o = returningFromStripe ? await api.confirmOrder(id) : await api.getOrder(id);
        if (!alive) return;
        setOrder(o);
        if (o.status === 'preordered') {
          clearCart();
          try { sessionStorage.removeItem('solemate-pending-order'); } catch
          setChecking(false);
        } else if (returningFromStripe && tries.current++ < 10) {
          timer = window.setTimeout(tick, 2000);
        } else {
          setChecking(false);
        }
      } catch (e) {
        if (alive) { setError((e as Error).message); setChecking(false); }
      }
    };
    void tick();
    return () => { alive = false; window.clearTimeout(timer); };
  }, [id, returningFromStripe, clearCart]);

  if (error) return <div className="container"><div className="alert error">{error}</div></div>;
  if (!order) return <div className="container"><div className="spinner" /></div>;
  const st = STATUS[order.status] ?? { label: order.status.replace(/_/g, ' '), tone: '' };

  return (
    <div className="container narrow stack">
      <span className={`pill ${st.tone}`}>{st.label}</span>
      {order.status === 'preordered' ? (
        <>
          <h1>Thanks, {order.customer_name}. Your preorder is in.</h1>
          <p>
            We charged {formatPrice(order.amount_paid_cents, order.currency)} for order <code>{order.id}</code>. Your shoes have not been made yet.
            {' '}{order.ship_estimate} A receipt is sent to {order.email}.
          </p>
        </>
      ) : checking ? (
        <>
          <h1>Confirming your payment…</h1>
          <div className="spinner" />
          <p className="small">This usually takes a few seconds. Please do not close this page.</p>
        </>
      ) : (
        <>
          <h1>This preorder is not paid yet</h1>
          <p>Nothing has been charged. {order.status === 'awaiting_payment' && <>Go back to <Link to="/checkout">checkout</Link> to complete it.</>}</p>
        </>
      )}
      <div className="card stack">
        {order.items.map((i, idx) => (
          <div key={idx} className="row between">
            <span>{i.quantity} × {i.shoe_name} <span className="pill warning">Preorder</span></span>
            <span>{formatPrice(i.line_cents, order.currency)}</span>
          </div>
        ))}
        <div className="price-lines"><div className="total"><span>Total</span><span>{formatPrice(order.total_cents, order.currency)}</span></div></div>
      </div>
      <p className="small muted">Questions or want to cancel before production? See the <Link to="/terms">Preorder Terms</Link>.</p>
      <Link className="btn ghost" to="/shoes">Preorder another pair</Link>
    </div>
  );
}
