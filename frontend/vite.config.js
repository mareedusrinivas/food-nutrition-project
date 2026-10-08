import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to the Flask backend (app.py running on port 5000)
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      // Live camera feed (multipart/x-mixed-replace stream from Flask /live_feed)
      '/live_feed': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      // Uploaded images served by Flask from static/uploads
      '/static/uploads': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
});
