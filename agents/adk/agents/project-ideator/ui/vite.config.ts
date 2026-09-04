import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/apps': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        headers: {
          origin: 'http://127.0.0.1:8000',
          referer: 'http://127.0.0.1:8000/',
        },
      },
      '/run_sse': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        headers: {
          origin: 'http://127.0.0.1:8000',
          referer: 'http://127.0.0.1:8000/',
        },
      },
      '/run': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        headers: {
          origin: 'http://127.0.0.1:8000',
          referer: 'http://127.0.0.1:8000/',
        },
      },
      '/list-apps': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        headers: {
          origin: 'http://127.0.0.1:8000',
          referer: 'http://127.0.0.1:8000/',
        },
      },
    },
  },
});
