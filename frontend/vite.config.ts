import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// The API server serves the built assets from the same origin in production, so
// during development we proxy instead of enabling CORS (§13). Point the proxy
// somewhere else with ONTOFORGE_API when the backend is not on the usual port.
const API_TARGET = process.env.ONTOFORGE_API ?? 'http://127.0.0.1:8080';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': API_TARGET,
      '/sparql': API_TARGET,
      '/mcp': API_TARGET,
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
