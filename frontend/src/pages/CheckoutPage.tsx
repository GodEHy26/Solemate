import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, formatPrice } from '../lib/api';
import { useCart } from '../store/useCart';
import { useFeet } from '../store/useFeet';

export function CheckoutPage() {
  const navigate = useNavigate();
  const { items, remove, setQuantity, clear } = useCart();
  const feet = useFeet((s) => s.profiles);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ customer_name: '', email: '', line1: '', line2: '', city: '', region: '', postal_code: '', country: '', notes: '' });

  const subtotal = items.reduce((n, i) => n + i.unit_cents * i.quantity, 0);
  const needsScan = items.some((i) => i.requires_scan) && !(feet.left && feet.right);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const order = await api.createOrder({
        customer_name: form.customer_name,
        email: form.email,
        shipping: { line1: form.line1, line2: form.line2 || null, city: form.city, region: form.region || null, postal_code: form.postal_code, country: form.country },
        notes: form.notes || null,
        items: items.map((i) => ({
          shoe_slug: i.shoe_slug,
          selections: i.selections,
          colors: i.colors,
          quantity: i.quantity,
          left_profile_id: feet.left ?? null,
          right_profile_id: feet.right ?? null,
        })),
      });
      clear();
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (items.length === 0) {
    return (
      <div className="container narrow stack">
        <h1>Your cart is empty</h1>
        <Link className="btn primary" to="/shoes">Browse shoes</Link>
      </div>
    );
  }

  return (
    <div className="container stack">
      <h1>Checkout</h1>
      {error && <div className="alert error">{error}</div>}
      <div className="grid two">
        <form className="card stack" onSubmit={submit}>
          <h3>Delivery</h3>
          <div className="grid">
            <label className="field">Name<input type="text" required value={form.customer_name} onChange={set('customer_name')} /></label>
            <label className="field">Email<input type="email" required value={form.email} onChange={set('email')} /></label>
          </div>
          <label className="field">Address line 1<input type="text" required value={form.line1} onChange={set('line1')} /></label>
          <label className="field">Address line 2<input type="text" value={form.line2} onChange={set('line2')} /></label>
          <div className="grid">
            <label className="field">City<input type="text" required value={form.city} onChange={set('city')} /></label>
            <label className="field">Region / state<input type="text" value={form.region} onChange={set('region')} /></label>
            <label className="field">Postal code<input type="text" required value={form.postal_code} onChange={set('postal_code')} /></label>
            <label className="field">Country<input type="text" required value={form.country} onChange={set('country')} placeholder="ISO code, e.g. KR" /></label>
          </div>
          <label className="field">Notes for the workshop<textarea rows={3} value={form.notes} onChange={set('notes')} /></label>
          <div className="small muted">
            Feet on file: left {feet.left ? '✓' : '✗'} · right {feet.right ? '✓' : '✗'}
            {needsScan && <span> — an item needs both feet scanned. <Link to="/scan">Scan now</Link>.</span>}
          </div>
          <button className="btn primary lg" type="submit" disabled={submitting || needsScan}>
            {submitting ? 'Placing order…' : `Place order · ${formatPrice(subtotal)}`}
          </button>
          <p className="small muted">Payment is collected after the workshop confirms the build (payment integration is on the roadmap).</p>
        </form>

        <div className="card stack">
          <h3>Items</h3>
          {items.map((i) => (
            <div key={i.id} className="card surface stack">
              <div className="row between">
                <strong>{i.shoe_name}</strong>
                <span>{formatPrice(i.unit_cents)}</span>
              </div>
              <div className="small muted">{Object.entries(i.selections).map(([k, v]) => `${k}: ${v.replace(/_/g, ' ')}`).join(' · ')}</div>
              <div className="row between">
                <label className="field" style={{ width: 90 }}>Qty<input type="number" min={1} max={10} value={i.quantity} onChange={(e) => setQuantity(i.id, Number(e.target.value))} /></label>
                <button type="button" className="btn danger" onClick={() => remove(i.id)}>Remove</button>
              </div>
            </div>
          ))}
          <div className="price-lines"><div className="total"><span>Subtotal</span><span>{formatPrice(subtotal)}</span></div></div>
        </div>
      </div>
    </div>
  );
}
