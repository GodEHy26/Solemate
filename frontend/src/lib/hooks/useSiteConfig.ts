import { useEffect, useState } from 'react';
import { api } from '../api';
import type { SiteConfig } from '../types';

// One request per page load, shared by every component.
let cached: Promise<SiteConfig> | null = null;
const load = () => (cached ??= api.config().catch((e) => {
  cached = null;
  throw e;
}));

export function useSiteConfig(): SiteConfig | null {
  const [cfg, setCfg] = useState<SiteConfig | null>(null);
  useEffect(() => {
    let alive = true;
    load().then((c) => alive && setCfg(c)).catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);
  return cfg;
}
