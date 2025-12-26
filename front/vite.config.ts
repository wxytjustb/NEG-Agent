import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // 代理 Golang 后端接口
      '/app': {
        target: 'https://app-api.roky.work',
        changeOrigin: true,
        secure: false, // 如果是 https 且证书有问题，设置为 false
      }
    }
  }
})
