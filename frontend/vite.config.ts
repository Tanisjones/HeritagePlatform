import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      strategies: 'injectManifest',
      srcDir: 'src/sw',
      filename: 'service-worker.js',
      injectManifest: {
        swSrc: 'src/sw/service-worker.js',
      },
      // A static manifest lives in public/manifest.json and is linked manually
      // from index.html, so the plugin must not generate or inject its own.
      manifest: false,
      injectRegister: null,
      registerType: 'autoUpdate',
      devOptions: {
        enabled: true,
        type: 'module',
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
