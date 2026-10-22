import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  // Pass /api/... on to FastAPI, so the browser sees one site (D17)
  // and the refresh cookie works without cross-site settings.
  // ws: true also passes the live line (WebSocket at /api/live) through (D19).
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', ws: true },
    },
  },
})
