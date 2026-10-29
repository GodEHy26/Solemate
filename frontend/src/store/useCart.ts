import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CartItem } from '../lib/types';

interface CartState {
  items: CartItem[];
  add: (item: Omit<CartItem, 'id'>) => void;
  remove: (id: string) => void;
  setQuantity: (id: string, quantity: number) => void;
  clear: () => void;
}

export const useCart = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      add: (item) =>
        set((s) => ({ items: [...s.items, { ...item, id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}` }] })),
      remove: (id) => set((s) => ({ items: s.items.filter((i) => i.id !== id) })),
      setQuantity: (id, quantity) =>
        set((s) => ({ items: s.items.map((i) => (i.id === id ? { ...i, quantity: Math.max(1, Math.min(10, quantity)) } : i)) })),
      clear: () => set({ items: [] }),
    }),
    { name: 'solemate-cart' },
  ),
);
