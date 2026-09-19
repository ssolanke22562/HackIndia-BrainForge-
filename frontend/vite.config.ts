import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/capture': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/classify': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/link': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/graph': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ask': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/history': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/persona': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
});
