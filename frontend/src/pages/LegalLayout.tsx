import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useSiteConfig } from '../lib/hooks/useSiteConfig';

export function LegalLayout({ title, children }: { title: string; children: ReactNode }) {
  const cfg = useSiteConfig();
  return (
    <div className="container narrow stack legal">
      <div>
        <Link to="/" className="small">← Home</Link>
        <h1>{title}</h1>
        <p className="small">Version {cfg?.terms_version ?? '…'}</p>
      </div>
      {cfg && !cfg.legal.configured && (
        <div className="alert warning">
          Operator details are not set yet. Before launch, set SOLEMATE_COMPANY_NAME and SOLEMATE_SUPPORT_EMAIL
          on the server so this page names who you are dealing with.
        </div>
      )}
      {children}
    </div>
  );
}

export function useOperator() {
  const cfg = useSiteConfig();
  const l = cfg?.legal;
  return {
    cfg,
    name: l?.company_name || '[operator name not set]',
    email: l?.support_email || '[contact email not set]',
    address: l?.company_address || '',
    law: l?.governing_law || '',
  };
}
