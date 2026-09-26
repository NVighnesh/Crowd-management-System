import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const apiBaseUrl = loadEnv(mode, process.cwd(), 'VITE_').VITE_API_BASE_URL?.trim()

  if (mode === 'production' && !apiBaseUrl) {
    throw new Error('VITE_API_BASE_URL is required for a production build')
  }

  if (apiBaseUrl) {
    console.info('VITE_API_BASE_URL is available to the Vite build.')
  }

  return {
    plugins: [react()],
  }
})
