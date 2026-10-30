import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

// Project page: https://sujay-r.github.io/tekken-counter-calculator/
const BASE = '/tekken-counter-calculator/'

export default defineConfig({
  base: BASE,
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      workbox: {
        // Both data files are imported by the app, so they are inlined into
        // the JS bundle; precaching the shell therefore covers the data too.
        globPatterns: ['**/*.{js,css,html,svg,png,ico,webmanifest}'],
        navigateFallback: `${BASE}index.html`,
        cleanupOutdatedCaches: true,
        // The bundled opponent index is ~1.1 MB minified; keep it cacheable.
        maximumFileSizeToCacheInBytes: 6 * 1024 * 1024,
      },
      manifest: {
        name: 'Tekken Counter Calculator — Steve',
        short_name: 'Steve Counter',
        description:
          'Which Steve move beats that move? Block, whiff and counter-hit punish lookups, offline.',
        theme_color: '#0f172a',
        background_color: '#0f172a',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  build: {
    // Single-file data bundle; the warning is noise for this app.
    chunkSizeWarningLimit: 2000,
  },
})
