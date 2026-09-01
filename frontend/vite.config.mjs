import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig, transformWithOxc } from 'vite';

const transformJsxInJs = () => ({
  name: 'transform-jsx-in-js',
  enforce: 'pre',
  async transform(code, id) {
    if (!id.includes('/src/') || !id.endsWith('.js')) {
      return null;
    }

    return transformWithOxc(code, id, { lang: 'jsx' });
  },
});

export default defineConfig({
  plugins: [transformJsxInJs(), react()],
  resolve: {
    alias: {
      'react-meta-tags': fileURLToPath(
        new URL('./src/components/meta-tags/index.js', import.meta.url),
      ),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
});
