import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The landing page (index.html) is plain HTML on the kit in public/assets; the console is the React app under /app.
const appFallback = {
  name: 'app-fallback',
  configureServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url === '/app' || (req.url.startsWith('/app/') && !req.url.includes('.'))) req.url = '/app/index.html'
      next()
    })
  },
}

const FRAME_HEADERS = { 'X-Frame-Options': 'DENY', 'Content-Security-Policy': "frame-ancestors 'none'" }

export default defineConfig({
  plugins: [react(), tailwindcss(), appFallback],
  appType: 'mpa',
  // The console must not be framed by another site (clickjacking on "Approve reply").
  server: { proxy: { '/api': 'http://localhost:8000' }, headers: FRAME_HEADERS },
  preview: { proxy: { '/api': 'http://localhost:8000' }, headers: FRAME_HEADERS },
  build: {
    assetsDir: 'static',
    rollupOptions: { input: { main: fileURLToPath(new URL('index.html', import.meta.url)), app: fileURLToPath(new URL('app/index.html', import.meta.url)) } },
  },
})
