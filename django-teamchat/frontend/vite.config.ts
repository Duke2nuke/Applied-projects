import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// TeamChat frontend. The Django API runs on http://127.0.0.1:8000
// (see ../README.md); set VITE_API_URL to point elsewhere.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})
