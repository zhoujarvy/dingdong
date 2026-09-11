import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
  build: {
    outDir: '../server/static',
    emptyOutDir: true,
    rollupOptions: {
      // 多页入口：main = 管理后台（/admin），site = 官网首页（/，纯 HTML）
      input: {
        main: resolve(__dirname, 'index.html'),
        site: resolve(__dirname, 'site.html'),
      },
    },
  },
})
