// Thin typed client for the SoleMate API. All paths are relative so the Vite
// dev proxy (or a production reverse proxy) decides where the backend lives.
import type {
  CapturePlan,
  FootProfile,
  OrderOut,
  PriceResult,
  ScanSession,
  ShoeDetail,
  ShoeSummary,
  Side,
} from './types';

/** Set VITE_API_BASE (e.g. https://api.example.com) when the API lives on a different origin. */
export const API_BASE: string = ((import.meta.env.VITE_API_BASE as string | undefined) ?? '').replace(/\/$/, '');

/** Turn an API-relative path such as /api/profiles/x/mesh.glb into a full URL. */
export const apiUrl = (path: string) => (path.startsWith('http') ? path : `${API_BASE}${path}`);

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<{ status: string }>('/api/health'),

  // Scans ----------------------------------------------------------------
  capturePlan: () => request<CapturePlan>('/api/scans/plan'),
  createScan: (side: Side, opts: { known_length_mm?: number; paper_size?: string } = {}) =>
    request<ScanSession>('/api/scans', json({ side, ...opts })),
  getScan: (id: string) => request<ScanSession>(`/api/scans/${id}`),
  uploadFrame: (id: string, blob: Blob, meta: { yaw_deg: number; pitch_deg: number; kind: 'orbit' | 'topdown' }) => {
    const form = new FormData();
    form.append('image', blob, `${meta.kind}.jpg`);
    form.append('yaw_deg', String(meta.yaw_deg));
    form.append('pitch_deg', String(meta.pitch_deg));
    form.append('kind', meta.kind);
    return request<ScanSession>(`/api/scans/${id}/frames`, { method: 'POST', body: form });
  },
  uploadMesh: (id: string, file: File, units = 'mm') => {
    const form = new FormData();
    form.append('mesh', file, file.name);
    form.append('units', units);
    return request<ScanSession>(`/api/scans/${id}/mesh`, { method: 'POST', body: form });
  },
  reconstruct: (id: string) => request<ScanSession>(`/api/scans/${id}/reconstruct`, { method: 'POST' }),

  // Profiles -------------------------------------------------------------
  getProfile: (id: string) => request<FootProfile>(`/api/profiles/${id}`),
  getLastSpec: (id: string, shoe?: string) =>
    request<Record<string, unknown>>(`/api/profiles/${id}/last-spec${shoe ? `?shoe=${encodeURIComponent(shoe)}` : ''}`),

  // Catalog --------------------------------------------------------------
  listShoes: () => request<{ shoes: ShoeSummary[] }>('/api/catalog/shoes').then((r) => r.shoes),
  getShoe: (slug: string) => request<ShoeDetail>(`/api/catalog/shoes/${slug}`),
  price: (shoe_slug: string, selections: Record<string, string>) =>
    request<PriceResult>('/api/catalog/price', json({ shoe_slug, selections })),

  // Orders ---------------------------------------------------------------
  createOrder: (body: unknown) => request<OrderOut>('/api/orders', json(body)),
  getOrder: (id: string) => request<OrderOut>(`/api/orders/${id}`),
};

/** Poll a scan until it leaves the processing state. */
export async function waitForScan(id: string, onTick?: (s: ScanSession) => void, intervalMs = 1500): Promise<ScanSession> {
  for (;;) {
    const s = await api.getScan(id);
    onTick?.(s);
    if (s.status === 'complete' || s.status === 'failed') return s;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export const formatPrice = (cents: number, currency = 'USD') =>
  new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(cents / 100);
