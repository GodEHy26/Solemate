import { LegalLayout, useOperator } from './LegalLayout';

export function PrivacyPage() {
  const { cfg, name, email, address } = useOperator();
  const stale = cfg?.legal.stale_session_hours ?? 24;
  const unpaid = cfg?.legal.unpaid_order_hours ?? 48;
  return (
    <LegalLayout title="Privacy Policy">
      <p>
        This policy explains what {name} (“SoleMate”, “we”) collects when you scan your feet and place a preorder,
        why, who sees it, how long we keep it, and how you can delete it.
      </p>

      <section className="card stack">
        <h3>Who is responsible</h3>
        <p>{name}{address ? `, ${address}` : ''}. Contact for anything in this policy: <a href={`mailto:${email}`}>{email}</a>.</p>
      </section>

      <section className="card stack">
        <h3>What we collect</h3>
        <ul>
          <li><strong>Foot photos.</strong> During a scan your phone takes a top-down photo on a sheet of paper and a series of photos around your foot. Each photo is sent to our server together with the angle it was taken at.</li>
          <li><strong>Camera and motion sensors.</strong> Your browser asks permission first. The camera is used only during the scan. Motion sensor readings stay in your browser and are used to guide the sweep; only the resulting angle for each photo is sent.</li>
          <li><strong>Your 3D foot model and measurements.</strong> Built from the photos: a 3D mesh, lengths, widths, girths, a footprint outline and size suggestions.</li>
          <li><strong>Order details.</strong> Name, email, delivery address, optional notes, what you chose, prices, and a record of when you accepted the preorder terms.</li>
          <li><strong>Payment status.</strong> You pay on a page hosted by Stripe. We never see your card number. We receive whether the payment succeeded, the amount, and a Stripe reference.</li>
          <li><strong>Technical data.</strong> Our hosting provider’s server logs (such as IP address and request time) for security and troubleshooting. We do not run analytics or advertising trackers.</li>
          <li><strong>Browser storage.</strong> Your cart, the IDs of your scanned feet and whether you dismissed the install banner are kept in your browser’s local storage so the site works. They are not used for tracking.</li>
        </ul>
      </section>

      <section className="card stack">
        <h3>Why we use it</h3>
        <ul>
          <li>To build your 3D model and make shoes that fit (needed to fulfil your preorder).</li>
          <li>To take payment, confirm and deliver your preorder, and contact you about it.</li>
          <li>To keep financial records we are legally required to keep, and to prevent fraud and abuse.</li>
        </ul>
        <p>We do not sell your data and we do not use your photos or foot model to train AI systems.</p>
      </section>

      <section className="card stack">
        <h3>Who we share it with</h3>
        <ul>
          <li><strong>Stripe</strong> processes your payment.</li>
          <li><strong>Our hosting provider</strong> stores the data on our behalf.</li>
          <li><strong>The workshop and delivery carrier</strong> that make and ship your pair receive the measurements needed to make the shoes and your delivery details.</li>
          <li>Authorities, where the law requires it.</li>
        </ul>
        <p>Some of these providers may process data outside your country.</p>
      </section>

      <section className="card stack">
        <h3>How long we keep it</h3>
        <ul>
          <li><strong>Photos:</strong> deleted automatically as soon as your 3D model has been built.</li>
          <li><strong>Unfinished or failed scans:</strong> deleted automatically after {stale} hours.</li>
          <li><strong>Orders you never paid for:</strong> deleted automatically after {unpaid} hours.</li>
          <li><strong>3D model and measurements:</strong> kept until you delete them. You can do this yourself on your foot profile page. If a scan is attached to an open preorder we need it to make your shoes, so deletion waits until that preorder is cancelled or finished.</li>
          <li><strong>Paid order records:</strong> kept as long as tax and accounting law requires, which is commonly several years depending on the country.</li>
        </ul>
      </section>

      <section className="card stack">
        <h3>Your rights</h3>
        <p>
          Depending on where you live you may have the right to access, correct, delete, export or object to our use
          of your data, and to complain to your data protection authority. Email <a href={`mailto:${email}`}>{email}</a> and
          we will respond within the time the law allows. Scan deletion is also available directly on your foot profile page.
        </p>
      </section>

      <section className="card stack">
        <h3>Security</h3>
        <p>
          Data travels over HTTPS. There are no accounts yet, so access to your scan and order pages relies on a long
          random link. Please do not share those links. If you think a link was exposed, email us and we will delete the data.
        </p>
      </section>

      <section className="card stack">
        <h3>Children</h3>
        <p>SoleMate is not directed at children under 16. If you believe a child has sent us data, email us and we will delete it.</p>
      </section>

      <section className="card stack">
        <h3>Changes</h3>
        <p>If we change this policy we will update the version date above and, for material changes, email customers with open preorders.</p>
      </section>
    </LegalLayout>
  );
}
