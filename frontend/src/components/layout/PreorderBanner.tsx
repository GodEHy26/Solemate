import { useSiteConfig } from '../../lib/hooks/useSiteConfig';

/** Always-visible reminder that nothing is in stock: every pair is a made-to-order preorder. */
export function PreorderBanner() {
  const cfg = useSiteConfig();
  return (
    <div className="preorder-banner" role="note">
      <strong>PREORDER</strong>
      <span>Made to order from your scan. {cfg?.ship_estimate ?? 'Estimated shipping: to be announced.'}</span>
    </div>
  );
}
