import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Side } from '../lib/types';

interface FeetState {
  profiles: Partial<Record<Side, string>>;
  setProfile: (side: Side, profileId: string) => void;
  clear: () => void;
}

export const useFeet = create<FeetState>()(
  persist(
    (set) => ({
      profiles: {},
      setProfile: (side, profileId) => set((s) => ({ profiles: { ...s.profiles, [side]: profileId } })),
      clear: () => set({ profiles: {} }),
    }),
    { name: 'solemate-feet' },
  ),
);
