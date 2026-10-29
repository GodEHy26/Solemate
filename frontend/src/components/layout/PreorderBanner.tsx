import { useSiteConfig } from '../../lib/hooks/useSiteConfig';

export function PreorderBanner() {
  const cfg = useSiteConfig();
  return (
    <div className="preorder-banner" role="note">
      <strong>PREORDER</strong>
      <span>Made to order from your scan. {cfg?.ship_estimate ?? 'Estimated shipping: to be announced.'}</span>
    </div>
  );
}
