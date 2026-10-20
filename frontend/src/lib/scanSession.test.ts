import { describe, expect, it } from 'vitest';
import {
  coverageFraction,
  createRing,
  isComplete,
  largestGapDeg,
  manualAdvance,
  markCovered,
  nextTargetSector,
  sectorOf,
  shouldCapture,
  startSweep,
  yawJitter,
} from './scanSession';

describe('ring sectors', () => {
  it('maps yaw to sectors with wrap-around', () => {
    expect(sectorOf(0, 15)).toBe(0);
    expect(sectorOf(359.9, 15)).toBe(23);
    expect(sectorOf(-5, 15)).toBe(23);
    expect(sectorOf(375, 15)).toBe(1);
  });

  it('tracks coverage and gaps', () => {
    let ring = createRing(15);
    expect(largestGapDeg(ring)).toBe(360);
    for (let s = 0; s < 12; s++) ring = markCovered(ring, s, s);
    expect(coverageFraction(ring)).toBeCloseTo(0.5);
    expect(largestGapDeg(ring)).toBe(180);
    expect(isComplete(ring)).toBe(false);
    for (let s = 12; s < 24; s += 2) ring = markCovered(ring, s, s);
    expect(largestGapDeg(ring)).toBe(15);
    expect(isComplete(ring)).toBe(true);
  });

  it('suggests the next uncovered sector clockwise', () => {
    let ring = createRing(15);
    ring = markCovered(ring, 5, 0);
    ring = markCovered(ring, 6, 0);
    expect(nextTargetSector(ring, 5)).toBe(7);
    expect(nextTargetSector(ring, 23)).toBe(23);
  });
});

describe('capture decisions', () => {
  it('needs a started sweep and a steady device', () => {
    let ring = createRing(15);
    expect(shouldCapture(ring, 90, 0, 0).reason).toBe('no-yaw');
    ring = startSweep(ring, 90); // device yaw 90 becomes relative 0
    expect(shouldCapture(ring, 90, 0, 1000)).toMatchObject({ capture: true, sector: 0 });
    expect(shouldCapture(ring, 90, 20, 1000).reason).toBe('unstable');
    ring = markCovered(ring, 0, 1000);
    expect(shouldCapture(ring, 92, 0, 1100).reason).toBe('covered');
    expect(shouldCapture(ring, 110, 0, 1100).reason).toBe('cooldown');
    expect(shouldCapture(ring, 110, 0, 2000)).toMatchObject({ capture: true, sector: 1 });
  });

  it('estimates jitter across the 360 boundary', () => {
    expect(yawJitter([358, 359, 1, 2])).toBeLessThan(3);
    expect(yawJitter([10, 30])).toBe(20);
  });

  it('manual mode walks the ring in order', () => {
    let ring = createRing(90);
    const sectors: number[] = [];
    for (let i = 0; i < 5; i++) {
      const r = manualAdvance(ring, i);
      ring = r.ring;
      sectors.push(r.sector ?? -1);
    }
    expect(sectors).toEqual([0, 1, 2, 3, -1]);
    expect(isComplete(ring)).toBe(true);
  });
});
