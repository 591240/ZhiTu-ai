import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 部署时由 Nginx 托管静态产物，API 走相对路径 /api（Nginx 反代到 backend:8000）
export default defineConfig({
  plugins: [vue()],
  base: '/',
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 600
  }
})
