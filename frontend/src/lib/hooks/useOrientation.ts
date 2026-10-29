import { useCallback, useEffect, useRef, useState } from 'react';
import { yawJitter } from '../scanSession';

export type OrientationStatus = 'idle' | 'needs-permission' | 'active' | 'unsupported' | 'denied';

interface OrientationState {
  status: OrientationStatus;
  yaw: number | null;   // compass-like heading in degrees (0-360)
  pitch: number | null; // device tilt: 90 = held vertically, 0 = flat
  jitter: number;       // recent yaw jitter in degrees
}

type DOEWithPermission = typeof DeviceOrientationEvent & { requestPermission?: () => Promise<'granted' | 'denied'> };

/**
 * Device heading from DeviceOrientation. iOS requires an explicit permission
 * request from a user gesture; call `request()` from a button handler.
 */
export function useDeviceOrientation(enabled: boolean) {
  const [state, setState] = useState<OrientationState>({ status: 'idle', yaw: null, pitch: null, jitter: 0 });
  const history = useRef<number[]>([]);

  const handler = useCallback((e: DeviceOrientationEvent) => {
    // webkitCompassHeading (iOS) is clockwise from north; alpha is counter-clockwise.
    const webkit = (e as DeviceOrientationEvent & { webkitCompassHeading?: number }).webkitCompassHeading;
    const yaw = typeof webkit === 'number' ? webkit : e.alpha !== null ? (360 - e.alpha) % 360 : null;
    if (yaw === null) return;
    const h = history.current;
    h.push(yaw);
    if (h.length > 8) h.shift();
    setState({ status: 'active', yaw, pitch: e.beta, jitter: yawJitter(h) });
  }, []);

  const request = useCallback(async () => {
    const DOE = (window as Window & { DeviceOrientationEvent?: DOEWithPermission }).DeviceOrientationEvent;
    if (!DOE) {
      setState((s) => ({ ...s, status: 'unsupported' }));
      return false;
    }
    if (typeof DOE.requestPermission === 'function') {
      try {
        const result = await DOE.requestPermission();
        if (result !== 'granted') {
          setState((s) => ({ ...s, status: 'denied' }));
          return false;
        }
      } catch {
        setState((s) => ({ ...s, status: 'denied' }));
        return false;
      }
    }
    window.addEventListener('deviceorientation', handler, true);
    setState((s) => ({ ...s, status: s.status === 'active' ? 'active' : 'needs-permission' }));
    // If no event arrives shortly, the device has no usable sensor.
    window.setTimeout(() => {
      setState((s) => (s.status === 'active' ? s : { ...s, status: 'unsupported' }));
    }, 2500);
    return true;
  }, [handler]);

  useEffect(() => {
    if (!enabled) return;
    const DOE = (window as Window & { DeviceOrientationEvent?: DOEWithPermission }).DeviceOrientationEvent;
    if (DOE && typeof DOE.requestPermission !== 'function') void request();
    else if (DOE) setState((s) => ({ ...s, status: 'needs-permission' }));
    else setState((s) => ({ ...s, status: 'unsupported' }));
    return () => window.removeEventListener('deviceorientation', handler, true);
  }, [enabled, handler, request]);

  return { ...state, request };
}
