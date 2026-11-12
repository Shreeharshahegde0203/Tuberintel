import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command, mode }) => {
  if (command === 'build' && process.env.VERCEL === '1') {
    const env = loadEnv(mode, process.cwd())
    const apiUrl = env.VITE_API_URL?.replace(/\/$/, '')
    if (!apiUrl || !/^https:\/\/[^/]+\/api\/v1$/.test(apiUrl)) {
      throw new Error('Set VITE_API_URL to the HTTPS backend URL ending in /api/v1.')
    }
    if (env.VITE_AUTH_MODE === 'supabase' && (!env.VITE_SUPABASE_URL || !env.VITE_SUPABASE_ANON_KEY)) {
      throw new Error('Supabase sign-in requires VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.')
    }
  }

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': 'http://127.0.0.1:8000',
        '/media': 'http://127.0.0.1:8000',
      },
    },
  }
})
