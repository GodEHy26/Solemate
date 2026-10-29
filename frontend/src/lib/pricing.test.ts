import { describe, expect, it } from 'vitest';
import { defaultColors, priceLocally } from './pricing';
import type { ShoeDetail } from './types';

const shoe: ShoeDetail = {
  slug: 's',
  name: 'S',
  tagline: '',
  description: '',
  category: 'x',
  last_family: 'x',
  base_price_cents: 10000,
  hero_color: '#000',
  allowed_options: {},
  defaults: {},
  components: [
    {
      id: 'outsole',
      name: 'Outsole',
      description: '',
      required: true,
      options: [
        { id: 'rubber', name: 'Rubber', material: '', price_delta_cents: 0, properties: {}, colors: ['#111'] },
        { id: 'pu', name: 'PU', material: '', price_delta_cents: 1500, properties: {}, colors: ['#222', '#333'] },
      ],
    },
    {
      id: 'insole',
      name: 'Insole',
      description: '',
      required: true,
      options: [{ id: 'printed', name: 'Printed', material: '', price_delta_cents: 4500, properties: {}, colors: [], requires_scan: true }],
    },
  ],
};

describe('local pricing', () => {
  it('sums deltas and flags missing/scan', () => {
    const p = priceLocally(shoe, { outsole: 'pu' });
    expect(p.total_cents).toBe(11500);
    expect(p.missing).toEqual(['Insole']);
    expect(p.requires_scan).toBe(false);
    const q = priceLocally(shoe, { outsole: 'rubber', insole: 'printed' });
    expect(q.total_cents).toBe(14500);
    expect(q.requires_scan).toBe(true);
  });

  it('picks first swatch as default colour', () => {
    expect(defaultColors(shoe, { outsole: 'pu' })).toEqual({ outsole: '#222' });
  });
});
