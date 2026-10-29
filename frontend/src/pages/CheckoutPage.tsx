import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api, formatPrice } from '../lib/api';
import { useFitCheck } from '../lib/hooks/useFitCheck';
import { useSiteConfig } from '../lib/hooks/useSiteConfig';
import { FitNotice } from '../components/fit/FitNotice';
import { useCart } from '../store/useCart';
import { useFeet } from '../store/useFeet';

export function CheckoutPage() {
  const cfg = useSiteConfig();
  const [params] = useSearchParams();
  const { items, remove, setQuantity } = useCart();
  const feet = useFeet((s) => s.profiles);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [ackScan, setAckScan] = useState(false);
  const { fit, loading: fitLoading } = useFitCheck();
  const scanBlocked = Boolean(fit?.blocked);
  const needsAck = Boolean(fit?.needs_acknowledgement);
  const [form, setForm] = useState({ customer_name: '', email: '', line1: '', line2: '', city: '', region: '', postal_code: '', country: '', notes: '' });

  const subtotal = items.reduce((n, i) => n + i.unit_cents * i.quantity, 0);
  const feetReady = Boolean(feet.left && feet.right);
  const paymentsOff = cfg ? !cfg.payments_enabled : false;
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const order = await api.createOrder({
        customer_name: form.customer_name,
        email: form.email,
        shipping: { line1: form.line1, line2: form.line2 || null, city: form.city, region: form.region || null, postal_code: form.postal_code, country: form.country },
        notes: form.notes || null,
        accepted_terms: accepted,
        accepted_scan_warnings: needsAck && ackScan,
        items: items.map((i) => ({
          shoe_slug: i.shoe_slug,
          selections: i.selections,
          colors: i.colors,
          quantity: i.quantity,
          left_profile_id: feet.left ?? null,
          right_profile_id: feet.right ?? null,
        })),
      });
      try { sessionStorage.setItem('solemate-pending-order', order.id); } catch { /* storage unavailable */ }
      const { url } = await api.startCheckout(order.id);
      window.location.assign(url); // hosted Stripe page; it returns to /orders/<id>?paid=1
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  if (items.length === 0) {
    return (
      <div className="container narrow stack">
        <h1>Your preorder is empty</h1>
        <p>Pick a shoe and choose your components. Everything on SoleMate is a preorder.</p>
        <Link className="btn primary" to="/shoes">Browse shoes</Link>
      </div>
    );
  }

  return (
    <div className="container stack">
      <h1>Preorder checkout</h1>
      {params.get('cancelled') && <div className="alert warning">Payment was cancelled. Nothing was charged and your preorder is still here.</div>}
      {error && <div className="alert error">{error}</div>}
      {paymentsOff && <div className="alert warning">Payments are not switched on yet, so you cannot complete a preorder right now.</div>}
      {!feetReady && (
        <div className="alert warning">
          Every pair is made from your scan, so both feet must be scanned first (left {feet.left ? '✓' : '✗'}, right {feet.right ? '✓' : '✗'}).{' '}
          <Link to="/scan">Scan now</Link>.
        </div>
      )}
      <div className="grid two">
        <form className="card stack" onSubmit={submit}>
          <h3>Delivery</h3>
          <div className="grid">
            <label className="field">Name<input type="text" required autoComplete="name" value={form.customer_name} onChange={set('customer_name')} /></label>
            <label className="field">Email<input type="email" required autoComplete="email" value={form.email} onChange={set('email')} /></label>
          </div>
          <label className="field">Address line 1<input type="text" required autoComplete="address-line1" value={form.line1} onChange={set('line1')} /></label>
          <label className="field">Address line 2<input type="text" autoComplete="address-line2" value={form.line2} onChange={set('line2')} /></label>
          <div className="grid">
            <label className="field">City<input type="text" required autoComplete="address-level2" value={form.city} onChange={set('city')} /></label>
            <label className="field">Region / state<input type="text" autoComplete="address-level1" value={form.region} onChange={set('region')} /></label>
            <label className="field">Postal code<input type="text" required autoComplete="postal-code" value={form.postal_code} onChange={set('postal_code')} /></label>
            <label className="field">Country<input type="text" required autoComplete="country" value={form.country} onChange={set('country')} placeholder="ISO code, e.g. KR" /></label>
          </div>
          <label className="field">Notes for the workshop<textarea rows={3} value={form.notes} onChange={set('notes')} /></label>

          {fit && <FitNotice fit={fit} />}
          {scanBlocked && (
            <div className="alert error">You can't place this preorder until the problem above is fixed. Retake the scan, then come back.</div>
          )}
          {needsAck && (
            <label className="consent">
              <input type="checkbox" checked={ackScan} onChange={(e) => setAckScan(e.target.checked)} />
              <span>I understand the scan may be less accurate.</span>
            </label>
          )}
          <div className="alert success">
            <strong>Fit guarantee.</strong> If your scan-based size doesn't fit, we'll remake it or give a one-time full refund.{' '}
            <Link to="/fit-guarantee" target="_blank">How it works</Link>
          </div>
          <div className="alert">
            <strong>This is a preorder.</strong> Your shoes have not been made yet. {cfg?.ship_estimate} {cfg?.shipping_policy}
          </div>
          <label className="consent">
            <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
            <span>
              I understand this is a preorder and the shipping date is an estimate. I agree to the{' '}
              <Link to="/terms" target="_blank">Preorder Terms</Link> and have read the{' '}
              <Link to="/privacy" target="_blank">Privacy Policy</Link>.
            </span>
          </label>
          <button className="btn primary lg" type="submit" disabled={busy || !accepted || !feetReady || paymentsOff || fitLoading || scanBlocked || (needsAck && !ackScan)}>
            {busy ? 'Taking you to secure payment…' : `Pay ${formatPrice(subtotal)} and preorder`}
          </button>
          <p className="small muted">You pay on a page hosted by Stripe. We never see your card number.</p>
        </form>

        <div className="card stack">
          <h3>Your preorder</h3>
          {items.map((i) => (
            <div key={i.id} className="card surface stack">
              <div className="row between">
                <strong>{i.shoe_name} <span className="pill warning">Preorder</span></strong>
                <span>{formatPrice(i.unit_cents)}</span>
              </div>
              <div className="small muted">{Object.entries(i.selections).map(([k, v]) => `${k}: ${v.replace(/_/g, ' ')}`).join(' · ')}</div>
              <div className="row between">
                <label className="field" style={{ width: 90 }}>Qty<input type="number" min={1} max={10} value={i.quantity} onChange={(e) => setQuantity(i.id, Number(e.target.value))} /></label>
                <button type="button" className="btn danger" onClick={() => remove(i.id)}>Remove</button>
              </div>
            </div>
          ))}
          <div className="price-lines"><div className="total"><span>Total today</span><span>{formatPrice(subtotal)}</span></div></div>
        </div>
      </div>
    </div>
  );
}
