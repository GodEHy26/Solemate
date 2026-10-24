import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, formatPrice } from '../lib/api';
import { defaultColors, priceLocally } from '../lib/pricing';
import type { PriceResult, ShoeDetail } from '../lib/types';
import { ComponentPicker } from '../components/configurator/ComponentPicker';
import { PriceSummary } from '../components/configurator/PriceSummary';
import { ShoePreview } from '../components/configurator/ShoePreview';
import { useCart } from '../store/useCart';
import { useFeet } from '../store/useFeet';

export function ConfiguratorPage() {
  const { slug = '' } = useParams();
  const navigate = useNavigate();
  const [shoe, setShoe] = useState<ShoeDetail | null>(null);
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [colors, setColors] = useState<Record<string, string>>({});
  const [price, setPrice] = useState<PriceResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addToCart = useCart((s) => s.add);
  const feet = useFeet((s) => s.profiles);
  const feetReady = Boolean(feet.left && feet.right);

  useEffect(() => {
    api.getShoe(slug).then((s) => {
      setShoe(s);
      setSelections(s.defaults);
      setColors(defaultColors(s, s.defaults));
    }).catch((e: Error) => setError(e.message));
  }, [slug]);

  // Instant local estimate, then the server-validated price (debounced).
  const local = useMemo(() => (shoe ? priceLocally(shoe, selections) : null), [shoe, selections]);
  useEffect(() => {
    if (!shoe) return;
    setPending(true);
    const t = window.setTimeout(() => {
      api.price(shoe.slug, selections).then(setPrice).catch((e: Error) => setError(e.message)).finally(() => setPending(false));
    }, 250);
    return () => window.clearTimeout(t);
  }, [shoe, selections]);

  if (error) return <div className="container"><div className="alert error">{error}</div></div>;
  if (!shoe) return <div className="container"><div className="spinner" /></div>;

  const choose = (componentId: string, optionId: string) => {
    const next = { ...selections, [componentId]: optionId };
    setSelections(next);
    const opt = shoe.components.find((c) => c.id === componentId)?.options.find((o) => o.id === optionId);
    if (opt?.colors?.length && !opt.colors.includes(colors[componentId] ?? '')) {
      setColors((c) => ({ ...c, [componentId]: opt.colors[0] }));
    }
  };

  const add = () => {
    if (!price?.valid) return;
    addToCart({
      shoe_slug: shoe.slug,
      shoe_name: shoe.name,
      selections,
      colors,
      quantity: 1,
      unit_cents: price.total_cents,
      requires_scan: price.requires_scan,
    });
    navigate('/checkout');
  };

  const currency = price?.currency ?? 'USD';
  return (
    <div className="container stack">
      <div className="row between">
        <div>
          <Link to="/shoes" className="small">← All shoes</Link>
          <h1>{shoe.name} <span className="pill warning">Preorder</span></h1>
          <p>{shoe.description}</p>
        </div>
        <div className="stack" style={{ alignItems: 'flex-end' }}>
          <span className="pill">{shoe.category} · {shoe.last_family} last</span>
          <span className={`pill ${feetReady ? 'success' : 'warning'}`}>{feetReady ? 'both feet scanned' : `${(feet.left ? 1 : 0) + (feet.right ? 1 : 0)}/2 feet scanned`}</span>
        </div>
      </div>

      <div className="grid two">
        <div className="stack">
          <ShoePreview colors={colors} heroColor={shoe.hero_color} />
          {shoe.components.map((c) => (
            <ComponentPicker
              key={c.id}
              component={c}
              value={selections[c.id]}
              color={colors[c.id]}
              currency={currency}
              onChange={(o) => choose(c.id, o)}
              onColor={(hex) => setColors((prev) => ({ ...prev, [c.id]: hex }))}
            />
          ))}
        </div>
        <div>
          <PriceSummary
            price={price ?? (local ? { valid: local.missing.length === 0, currency, base_cents: local.base_cents, options_cents: local.options_cents, total_cents: local.total_cents, lines: [], errors: local.missing.map((m) => `Choose a ${m.toLowerCase()}.`), requires_scan: local.requires_scan } : null)}
            pending={pending}
            feetReady={feetReady}
            onAdd={add}
          />
        </div>
      </div>
      <div className="price-bar">
        <div>
          <div className="small muted">Preorder total</div>
          <strong>{price ? formatPrice(price.total_cents, currency) : '…'}</strong>
        </div>
        <button className="btn primary" disabled={!price?.valid || pending} onClick={add}>Preorder</button>
      </div>
    </div>
  );
}
