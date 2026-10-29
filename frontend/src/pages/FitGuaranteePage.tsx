// Fit guarantee (refund policy for scan-based sizing). Production hasn't started, so this is the
// policy orders will be made under once it does. The claim window and conditions are defaults:
// confirm them before launch (see docs/PAYMENTS.md).
import { Link } from 'react-router-dom';
import { LegalLayout, useOperator } from './LegalLayout';

const CLAIM_WINDOW_DAYS = 30;

export function FitGuaranteePage() {
  const { email } = useOperator();
  return (
    <LegalLayout title="Fit Guarantee">
      <div className="alert success">
        <strong>If your scan-based size doesn't fit, we'll remake it or give a one-time full refund.</strong>
      </div>
      <p className="small">
        Production hasn't started yet, so no pairs have shipped. This is the policy every pair will be made under once
        orders begin.
      </p>

      <section className="card stack">
        <h3>What's covered</h3>
        <p>
          Your pair doesn't fit because of the size or shape we made from your scan: too long, too short, too tight or
          too loose. This includes orders placed after you accepted a scan warning.
        </p>
      </section>

      <section className="card stack">
        <h3>What you get</h3>
        <ul>
          <li><strong>A remake.</strong> We may ask you to rescan first so the new pair is built on a better scan.</li>
          <li><strong>Or a full refund</strong> of what you paid for that pair, back to your original payment method.</li>
          <li>The full refund is available <strong>once per customer</strong>. After that, fit problems are fixed with a remake.</li>
        </ul>
      </section>

      <section className="card stack">
        <h3>How to claim</h3>
        <ul>
          <li>Email <a href={`mailto:${email}`}>{email}</a> within {CLAIM_WINDOW_DAYS} days of delivery with your order number and a photo of the shoes on your feet.</li>
          <li>Try the shoes indoors only, so we can tell fit problems apart from wear.</li>
          <li>If we ask for the pair back, we pay the return shipping.</li>
        </ul>
      </section>

      <section className="card stack">
        <h3>What isn't covered</h3>
        <ul>
          <li>Changing your mind about the style, colour or materials you chose.</li>
          <li>Wear and tear after outdoor use.</li>
          <li>Faulty pairs or pairs that aren't what you ordered: those are covered separately in the <Link to="/terms">Preorder Terms</Link>.</li>
        </ul>
        <p className="small">Your legal rights as a consumer are not affected.</p>
      </section>
    </LegalLayout>
  );
}
