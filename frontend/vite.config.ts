/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// VITE_BASE: '/' for Vercel/Netlify/Docker, '/<repo>/' for GitHub Pages project sites.
export default defineConfig(({ mode }) => {
  // One config file for the whole project: the repo-root .env (Vite only exposes VITE_* vars to the browser).
  const envDir = '..';
  const env = loadEnv(mode, envDir, '');
  return {
    envDir,
    base: env.VITE_BASE || '/',
    plugins: [react(), tailwindcss()],
    // Same-origin API in dev and preview: /api -> backend (VITE_API_URL, default http://localhost:8000)
    server: {
      port: 5173,
      proxy: {
        '/api': { target: env.VITE_API_URL || 'http://localhost:8000', changeOrigin: true },
      },
    },
    preview: {
      proxy: {
        '/api': { target: env.VITE_API_URL || 'http://localhost:8000', changeOrigin: true },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test-setup.ts'],
      globals: true,
      css: false,
      env: { VITE_MOCK: 'false' },
    },
  };
});
