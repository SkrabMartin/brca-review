import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';
export default defineConfig({ plugins: [react()], server: { proxy: { '/api/v1': 'http://127.0.0.1:8093' } }, test: { environment: 'jsdom' } });
