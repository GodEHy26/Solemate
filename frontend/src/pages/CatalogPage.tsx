import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, formatPrice } from '../lib/api';
import type { ShoeSummary } from '../lib/types';

export function CatalogPage() {
  const [shoes, setShoes] = useState<ShoeSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.listShoes().then(setShoes).catch((e: Error) => setError(e.message));
  }, []);
  return (
    <div className="container stack">
      <div>
        <h1>Shoes <span className="pill warning">Preorder</span></h1>
        <p>Every model is a preorder, built on your scanned last after you order. Pick a base, then choose each component.</p>
      </div>
      {error && <div className="alert error">{error}</div>}
      {!shoes ? <div className="spinner" /> : (
        <div className="grid">
          {shoes.map((s) => (
            <div key={s.slug} className="card shoe-card">
              <div className="swatch" style={{ ['--c' as string]: s.hero_color }} />
              <div className="row between">
                <h3>{s.name}</h3>
                <span className="pill warning">Preorder</span>
              </div>
              <p className="small">{s.tagline}</p>
              <div className="row between">
                <span className="muted small">preorder from {formatPrice(s.base_price_cents)}</span>
                <Link className="btn primary" to={`/shoes/${s.slug}`}>Customize and preorder</Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
