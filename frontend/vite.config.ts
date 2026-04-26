import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/register': 'http://127.0.0.1:8000',
      '/token': 'http://127.0.0.1:8000',
      '/users/me': 'http://127.0.0.1:8000',
      '/pokemon': 'http://127.0.0.1:8000',
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true
      }
    }
  }
})
