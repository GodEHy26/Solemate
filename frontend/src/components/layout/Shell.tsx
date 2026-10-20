import type { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useCart } from '../../store/useCart';
import { useFeet } from '../../store/useFeet';

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
          <NavLink to="/checkout">Cart {count > 0 && <span className="pill accent">{count}</span>}</NavLink>
        </nav>
      </header>
      <main style={{ flex: 1 }}>{children}</main>
      <footer className="footer">SoleMate · custom footwear from a 3D foot scan · successor to the IB Computer Science IA</footer>
    </div>
  );
}
