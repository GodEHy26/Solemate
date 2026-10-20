// Shapes returned by the SoleMate API (mirrors backend/app/schemas.py).

export type Side = 'left' | 'right';

export interface CapturePose {
  index: number;
  kind: 'topdown' | 'orbit';
  yaw_deg: number;
  pitch_deg: number;
  instruction: string;
}

export interface CapturePlan {
  sector_deg: number;
  sector_count: number;
  orbit_pitch_deg: number;
  min_orbit_frames: number;
  paper_sizes: string[];
  poses: CapturePose[];
}

export interface Coverage {
  fraction: number;
  missing_sectors: number[];
  largest_gap_deg: number;
  sector_count: number;
}

export interface ScanSession {
  id: string;
  side: Side;
  status: 'capturing' | 'processing' | 'complete' | 'failed';
  frame_count: number;
  frames: { index: number; kind: string; yaw_deg: number; pitch_deg: number }[];
  coverage: Coverage;
  known_length_mm: number | null;
  paper_size: string | null;
  error: string | null;
  profile_id: string | null;
}

export interface Measurements {
  length_mm: number;
  ball_width_mm: number;
  heel_width_mm: number;
  waist_width_mm: number;
  toe_width_mm: number;
  instep_height_mm: number;
  ball_height_mm: number;
  toe_height_mm: number;
  ball_girth_mm: number | null;
  waist_girth_mm: number | null;
  instep_girth_mm: number | null;
  ball_position_mm: number;
  waist_position_mm: number;
  instep_position_mm: number;
  volume_cm3: number;
}

export interface Sizing {
  foot_length_mm: number;
  toe_allowance_mm: number;
  foot: Record<string, number>;
  recommended: Record<string, number>;
  width: { code: string; label: string; ratio: number };
  notes: string[];
}

export interface Section {
  name: string;
  x_mm: number;
  pct: number;
  girth_mm: number | null;
  points: [number, number][];
}

export interface FootProfile {
  id: string;
  scan_session_id: string;
  side: Side;
  source: string;
  scale_method: string;
  scale_confidence: 'high' | 'medium' | 'low';
  measurements: Measurements;
  sizing: Sizing;
  footprint_mm: [number, number][];
  width_profile: { pct: number; x_mm: number; width_mm: number }[];
  height_profile: { pct: number; x_mm: number; height_mm: number }[];
  topdown: Record<string, unknown> | null;
  sections: Section[];
  warnings: string[];
  mesh_urls: { glb: string; obj: string };
  created_at: string;
}

export interface ComponentOption {
  id: string;
  name: string;
  material: string;
  price_delta_cents: number;
  properties: Record<string, number>;
  colors: string[];
  notes?: string;
  requires_scan?: boolean;
}

export interface ShoeComponent {
  id: string;
  name: string;
  description: string;
  required: boolean;
  options: ComponentOption[];
}

export interface ShoeSummary {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  category: string;
  last_family: string;
  base_price_cents: number;
  placeholder?: boolean;
  hero_color: string;
  allowed_options: Record<string, string[] | '*'>;
  defaults: Record<string, string>;
}

export interface ShoeDetail extends ShoeSummary {
  components: ShoeComponent[];
}

export interface PriceLine {
  component_id: string;
  component_name: string;
  option_id: string;
  option_name: string;
  cents: number;
}

export interface PriceResult {
  valid: boolean;
  currency: string;
  base_cents: number;
  options_cents: number;
  total_cents: number;
  lines: PriceLine[];
  errors: string[];
  requires_scan: boolean;
}

export interface CartItem {
  id: string;
  shoe_slug: string;
  shoe_name: string;
  selections: Record<string, string>;
  colors: Record<string, string>;
  quantity: number;
  unit_cents: number;
  requires_scan: boolean;
}

export interface OrderOut {
  id: string;
  status: string;
  customer_name: string;
  email: string;
  items: Array<{ shoe_name: string; quantity: number; line_cents: number; selections: Record<string, string> }>;
  currency: string;
  total_cents: number;
  created_at: string;
}
