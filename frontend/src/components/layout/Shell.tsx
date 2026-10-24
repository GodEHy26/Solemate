import type { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useCart } from '../../store/useCart';
import { useFeet } from '../../store/useFeet';
import { InstallPrompt } from './InstallPrompt';
import { PreorderBanner } from './PreorderBanner';

const icon = {
  home: <path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V11z" />,
  scan: <path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3M4 12h16" />,
  shoe: <path d="M3 16v-3l6-2 2 2 5 1c3 .5 5 1.5 5 3v1H3v-2zM3 19h18" />,
  cart: <path d="M3 4h2l2.4 11h10.2L20 7H6M9 20a1 1 0 1 0 0-.01M17 20a1 1 0 1 0 0-.01" />,
};

function Icon({ d }: { d: keyof typeof icon }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {icon[d]}
    </svg>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const count = useCart((s) => s.items.reduce((n, i) => n + i.quantity, 0));
  const feet = useFeet((s) => s.profiles);
  const scanned = (feet.left ? 1 : 0) + (feet.right ? 1 : 0);
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          SoleMate <span>3D</span>
        </Link>
        <nav className="nav">
          <NavLink to="/scan">Scan {scanned > 0 && <span className="pill accent">{scanned}/2</span>}</NavLink>
          <NavLink to="/shoes">Shoes</NavLink>
          <NavLink to="/checkout">Preorders {count > 0 && <span className="pill accent">{count}</span>}</NavLink>
        </nav>
      </header>
      <PreorderBanner />
      <InstallPrompt />
      <main style={{ flex: 1 }}>{children}</main>
      <footer className="footer">
        <span>SoleMate · every pair is a made-to-order preorder</span>
        <span className="footer-links"><Link to="/terms">Preorder Terms</Link><Link to="/privacy">Privacy Policy</Link></span>
      </footer>
      <nav className="tabbar" aria-label="Main">
        <NavLink to="/" end><Icon d="home" />Home</NavLink>
        <NavLink to="/scan"><Icon d="scan" />Scan{scanned > 0 && <span className="badge">{scanned}/2</span>}</NavLink>
        <NavLink to="/shoes"><Icon d="shoe" />Shoes</NavLink>
        <NavLink to="/checkout"><Icon d="cart" />Preorders{count > 0 && <span className="badge">{count}</span>}</NavLink>
      </nav>
    </div>
  );
}
