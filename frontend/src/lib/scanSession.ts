export interface RingState {
  sectorDeg: number;
  sectorCount: number;
  covered: boolean[];
  yawOffset: number | null;
  lastCaptureAt: number | null;
}

export interface CaptureDecision {
  capture: boolean;
  sector: number | null;
  reason: 'no-yaw' | 'covered' | 'unstable' | 'cooldown' | 'ok';
}

export const DEFAULT_SECTOR_DEG = 15;
export const MIN_COVERAGE = 0.75;
export const MAX_GAP_DEG = 60;
export const CAPTURE_COOLDOWN_MS = 350;

export function createRing(sectorDeg = DEFAULT_SECTOR_DEG): RingState {
  const sectorCount = Math.round(360 / sectorDeg);
  return { sectorDeg, sectorCount, covered: Array(sectorCount).fill(false), yawOffset: null, lastCaptureAt: null };
}

export const normalizeDeg = (deg: number) => ((deg % 360) + 360) % 360;

export function sectorOf(yawDeg: number, sectorDeg: number): number {
  const count = Math.round(360 / sectorDeg);
  return Math.floor(normalizeDeg(yawDeg) / (360 / count)) % count;
}


export function relativeYaw(ring: RingState, deviceYaw: number): number | null {
  if (ring.yawOffset === null) return null;
  return normalizeDeg(ring.yawOffset - deviceYaw);
}

export function startSweep(ring: RingState, deviceYaw: number): RingState {
  return { ...ring, yawOffset: deviceYaw, covered: ring.covered.map(() => false), lastCaptureAt: null };
}

export function markCovered(ring: RingState, sector: number, now: number): RingState {
  const covered = ring.covered.slice();
  covered[sector] = true;
  return { ...ring, covered, lastCaptureAt: now };
}

export function coverageFraction(ring: RingState): number {
  return ring.covered.filter(Boolean).length / ring.sectorCount;
}

export function missingSectors(ring: RingState): number[] {
  return ring.covered.map((c, i) => (c ? -1 : i)).filter((i) => i >= 0);
}

export function largestGapDeg(ring: RingState): number {
  const n = ring.sectorCount;
  if (ring.covered.every((c) => !c)) return 360;
  let best = 0;
  let run = 0;
  for (let i = 0; i < 2 * n; i++) {
    if (!ring.covered[i % n]) {
      run += 1;
      best = Math.max(best, Math.min(run, n));
    } else run = 0;
  }
  return best * ring.sectorDeg;
}

export function isComplete(ring: RingState, minCoverage = MIN_COVERAGE, maxGapDeg = MAX_GAP_DEG): boolean {
  return coverageFraction(ring) >= minCoverage && largestGapDeg(ring) <= maxGapDeg;
}

export function nextTargetSector(ring: RingState, currentSector: number | null): number | null {
  const n = ring.sectorCount;
  const start = currentSector ?? 0;
  for (let k = 0; k < n; k++) {
    const s = (start + k) % n;
    if (!ring.covered[s]) return s;
  }
  return null;
}


export function shouldCapture(
  ring: RingState,
  deviceYaw: number | null,
  stability: number,
  now: number,
  maxJitterDeg = 6,
): CaptureDecision {
  if (deviceYaw === null || ring.yawOffset === null) return { capture: false, sector: null, reason: 'no-yaw' };
  const rel = relativeYaw(ring, deviceYaw)!;
  const sector = sectorOf(rel, ring.sectorDeg);
  if (ring.covered[sector]) return { capture: false, sector, reason: 'covered' };
  if (stability > maxJitterDeg) return { capture: false, sector, reason: 'unstable' };
  if (ring.lastCaptureAt !== null && now - ring.lastCaptureAt < CAPTURE_COOLDOWN_MS)
    return { capture: false, sector, reason: 'cooldown' };
  return { capture: true, sector, reason: 'ok' };
}

export function yawJitter(samples: number[]): number {
  if (samples.length < 2) return 0;
  let maxDiff = 0;
  for (let i = 1; i < samples.length; i++) {
    const d = Math.abs(normalizeDeg(samples[i] - samples[i - 1] + 180) - 180);
    maxDiff = Math.max(maxDiff, d);
  }
  return maxDiff;
}

export function manualAdvance(ring: RingState, now: number): { ring: RingState; sector: number | null } {
  const sector = nextTargetSector(ring, null);
  if (sector === null) return { ring, sector: null };
  return { ring: markCovered(ring, sector, now), sector };
}
