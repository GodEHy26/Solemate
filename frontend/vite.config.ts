import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';

// The API runs separately (uvicorn on :8000). In dev, /api is proxied so the
// browser sees one origin; in production put both behind the same reverse proxy.
export default defineConfig({
  // VITE_HTTPS=1 serves the dev server over a self-signed certificate so a phone on your
  // Wi-Fi can use the camera and motion sensors (both require a secure context).
  plugins: [react(), ...(process.env.VITE_HTTPS ? [basicSsl()] : [])],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
  preview: {
    port: 4173,
    host: true,
    proxy: {
      '/api': { target: process.env.VITE_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: { three: ['three', '@react-three/fiber', '@react-three/drei'] },
      },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
