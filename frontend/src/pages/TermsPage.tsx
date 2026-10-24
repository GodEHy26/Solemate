// Template preorder terms. The refund and delay rules below are defaults chosen to be fair to
// customers; they are business decisions, so confirm them (and have the page reviewed) before launch.
import { LegalLayout, useOperator } from './LegalLayout';

const DELAY_GRACE_DAYS = 60;

export function TermsPage() {
  const { cfg, name, email, law } = useOperator();
  return (
    <LegalLayout title="Preorder Terms">
      <div className="alert">
        <strong>In short:</strong> every pair is a preorder. Your shoes do not exist yet. They are made to order from your
        scan, and the shipping date is an estimate.
      </div>

      <section className="card stack">
        <h3>1. What a preorder is</h3>
        <p>
          By placing a preorder with {name} you are paying to reserve a pair that will be made for you after production
          opens. Nothing is kept in stock. {cfg?.ship_estimate ?? ''} Dates are estimates, not promises.
        </p>
      </section>

      <section className="card stack">
        <h3>2. Price and payment</h3>
        <p>
          The price shown at checkout is charged in full when you pay, through Stripe. {cfg?.shipping_policy ?? ''}
          Prices are fixed once you have paid.
        </p>
      </section>

      <section className="card stack">
        <h3>3. Cancelling and refunds</h3>
        <ul>
          <li><strong>Before production starts:</strong> email <a href={`mailto:${email}`}>{email}</a> and we will refund you in full. We will email you before production on your pair begins.</li>
          <li><strong>After production starts:</strong> the shoes are made to your feet and cannot be resold, so we cannot cancel, except as below.</li>
          <li><strong>If we are late:</strong> if shipping is more than {DELAY_GRACE_DAYS} days later than the estimate we gave when you ordered, you may cancel for a full refund.</li>
          <li><strong>If something is wrong:</strong> if your pair does not match your scan, is faulty, or is not what you ordered, we will remake it or refund you.</li>
          <li>Refunds go back to the original payment method. Your legal rights as a consumer are not affected.</li>
        </ul>
      </section>

      <section className="card stack">
        <h3>4. Fit and your scan</h3>
        <p>
          Your shoes are made from the 3D model built from your scan, so a poor scan can mean a poor fit. We may ask you to
          rescan if the result looks unreliable. Sizes shown in the app are for orientation only.
        </p>
      </section>

      <section className="card stack">
        <h3>5. Changes to your preorder</h3>
        <p>
          Materials can run out. If we must substitute a component we will contact you first, and you may accept the
          substitute or cancel for a full refund.
        </p>
      </section>

      <section className="card stack">
        <h3>6. Your data</h3>
        <p>How we handle your photos, scan and order details is described in the Privacy Policy.</p>
      </section>

      <section className="card stack">
        <h3>7. Contact and governing law</h3>
        <p>
          Questions: <a href={`mailto:${email}`}>{email}</a>.
          {law ? ` These terms are governed by ${law}, without limiting any mandatory consumer rights where you live.` : ''}
        </p>
      </section>
    </LegalLayout>
  );
}
