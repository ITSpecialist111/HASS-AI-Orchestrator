import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    base: './', // Vital for HA Ingress
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            '/api': {
                target: 'http://localhost:8999',
                changeOrigin: true
            },
            '/ws': {
                target: 'ws://localhost:8999',
                ws: true
            }
        }
    },
    build: {
        outDir: 'dist',
        assetsDir: 'assets',
        emptyOutDir: true
    }
})
