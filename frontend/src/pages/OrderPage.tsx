import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, formatPrice } from '../lib/api';
import type { OrderOut } from '../lib/types';

export function OrderPage() {
  const { id = '' } = useParams();
  const [order, setOrder] = useState<OrderOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.getOrder(id).then(setOrder).catch((e: Error) => setError(e.message));
  }, [id]);
  if (error) return <div className="container"><div className="alert error">{error}</div></div>;
  if (!order) return <div className="container"><div className="spinner" /></div>;
  return (
    <div className="container narrow stack">
      <span className="pill success">order {order.status.replace('_', ' ')}</span>
      <h1>Thanks, {order.customer_name}.</h1>
      <p>Order <code>{order.id}</code> is in. We will email {order.email} when the workshop has reviewed your last and is ready to take payment.</p>
      <div className="card stack">
        {order.items.map((i, idx) => (
          <div key={idx} className="row between">
            <span>{i.quantity} × {i.shoe_name}</span>
            <span>{formatPrice(i.line_cents, order.currency)}</span>
          </div>
        ))}
        <div className="price-lines"><div className="total"><span>Total</span><span>{formatPrice(order.total_cents, order.currency)}</span></div></div>
      </div>
      <Link className="btn ghost" to="/shoes">Build another pair</Link>
    </div>
  );
}
