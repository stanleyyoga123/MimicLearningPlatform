import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const proxyTarget = loadEnv(mode, process.cwd(), 'API_PROXY_').API_PROXY_TARGET || 'http://127.0.0.1:8000';
  const proxyUrl = new URL(proxyTarget);
  if (!['http:', 'https:'].includes(proxyUrl.protocol)) throw new Error('API_PROXY_TARGET must be an HTTP URL.');
  return {
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: proxyUrl.origin, rewrite: (path) => path.replace(/^\/api/, '') } },
  },
  test: { environment: 'jsdom', setupFiles: './tests/setup.ts' },
  };
});
