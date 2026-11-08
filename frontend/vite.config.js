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

export default defineConfig({
  plugins: [react(), tailwindcss(), appFallback],
  appType: 'mpa',
  server: { proxy: { '/api': 'http://localhost:8000' } },
  build: {
    assetsDir: 'static',
    rollupOptions: { input: { main: fileURLToPath(new URL('index.html', import.meta.url)), app: fileURLToPath(new URL('app/index.html', import.meta.url)) } },
  },
})
