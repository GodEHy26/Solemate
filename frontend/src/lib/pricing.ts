import type { ShoeDetail } from './types';

export interface LocalPrice {
  base_cents: number;
  options_cents: number;
  total_cents: number;
  missing: string[];
  requires_scan: boolean;
}

export function priceLocally(shoe: ShoeDetail, selections: Record<string, string>): LocalPrice {
  let options = 0;
  let requiresScan = false;
  const missing: string[] = [];
  for (const comp of shoe.components) {
    const choice = selections[comp.id];
    const opt = comp.options.find((o) => o.id === choice);
    if (!opt) {
      if (comp.required) missing.push(comp.name);
      continue;
    }
    options += opt.price_delta_cents;
    requiresScan ||= Boolean(opt.requires_scan);
  }
  return {
    base_cents: shoe.base_price_cents,
    options_cents: options,
    total_cents: shoe.base_price_cents + options,
    missing,
    requires_scan: requiresScan,
  };
}


export function defaultColors(shoe: ShoeDetail, selections: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const comp of shoe.components) {
    const opt = comp.options.find((o) => o.id === selections[comp.id]);
    if (opt?.colors?.length) out[comp.id] = opt.colors[0];
  }
  return out;
}
