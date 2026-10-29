import { useEffect, useState } from 'react';
import { api } from '../api';
import type { FitCheck } from '../types';
import { useFeet } from '../../store/useFeet';

/** Pair-level scan check for the customer's current left and right scans (null until both exist). */
export function useFitCheck(): { fit: FitCheck | null; loading: boolean; error: string | null } {
  const { left, right } = useFeet((s) => s.profiles);
  const [fit, setFit] = useState<FitCheck | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!left || !right) {
      setFit(null);
      return;
    }
    let alive = true;
    setLoading(true);
    api.fitCheck(left, right)
      .then((f) => alive && (setFit(f), setError(null)))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [left, right]);
  return { fit, loading, error };
}
