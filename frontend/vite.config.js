import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy all backend API routes to FastAPI running on port 8000.
      // The browser sees everything as same-origin → cookies work with no CORS.
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/user': { target: 'http://localhost:8000', changeOrigin: true },
      '/chat': { target: 'http://localhost:8000', changeOrigin: true },
      '/file': { target: 'http://localhost:8000', changeOrigin: true },
      '/folder': { target: 'http://localhost:8000', changeOrigin: true },
      '/main': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
