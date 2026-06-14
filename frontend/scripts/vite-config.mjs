import vue from '@vitejs/plugin-vue'

export function createInlineViteConfig() {
  return {
    cacheDir: process.env.VITE_CACHE_DIR || 'node_modules/.vite',
    plugins: [vue()],
    build: {
      outDir: process.env.VITE_BUILD_OUT_DIR || 'dist',
    },
    optimizeDeps: {
      include: ['element-plus', 'vue', 'vue-router', 'axios'],
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
}
