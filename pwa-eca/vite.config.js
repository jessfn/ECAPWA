import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

// pwa-eca — configuración (ECA-011 + auto-actualización sin recarga manual,
// pedido explícito: "cada vez que se haga una deployada debe actualizarse
// inmediatamente la app aunque no se refresque el navegador").
//
// Un solo service worker (Workbox vía vite-plugin-pwa) — el inventario
// técnico (`02` §2) señaló el doble SW como problema conocido en el legado.
// `/api/**` es NetworkOnly a propósito: los datos de negocio (jornadas,
// actividades, etc.) no se sirven desde caché — la app offline funciona por
// la **sesión local** (`src/services/sesionLocal.js`) y el **outbox** de
// pendientes (ECA-016+), no por cachear respuestas de API.
//
// `BUILD_ID` (marca de tiempo del build) se inyecta como `__BUILD_ID__` y
// se escribe también en `dist/version.json`: `src/services/autoUpdate.js`
// sondea ese archivo y recarga sola la pestaña en cuanto detecta un build
// distinto al que tiene cargado — sin esperar a que el usuario refresque.
const BUILD_ID = String(Date.now())

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'eca-write-version',
      apply: 'build',
      generateBundle() {
        this.emitFile({ type: 'asset', fileName: 'version.json', source: JSON.stringify({ buildId: BUILD_ID }) })
      },
    },
    VitePWA({
      registerType: 'autoUpdate',
      // El registro del SW ya no lo inyecta el plugin: lo hace a mano
      // `src/services/autoUpdate.js` (vía `virtual:pwa-register`), para
      // poder forzar recarga inmediata en `onNeedRefresh` en vez del
      // registro por defecto que no recarga solo.
      injectRegister: false,
      manifest: {
        name: 'ECA — Técnicos',
        short_name: 'ECA Técnicos',
        description: 'App de campo para técnicos de Escuelas de Campo (ECA).',
        theme_color: '#0f4c26',
        background_color: '#d1fae5',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        // Bug real encontrado en producción: sin esto, un SW nuevo se
        // queda "esperando" (`waiting`) para siempre — `registerType:
        // 'autoUpdate'` en el cliente asume que el SW se activa solo
        // (escucha el evento `activated`, no manda `skipWaiting` él
        // mismo), pero Workbox NO activa un SW nuevo automáticamente a
        // menos que el propio SW llame `self.skipWaiting()` — que es
        // justo lo que faltaba aquí. Confirmado con
        // `registration.waiting` no nulo en producción, incluso tras
        // varios despliegues y recargas seguidas: la pestaña quedaba
        // sirviendo el `index.html`/JS del SW viejo indefinidamente.
        skipWaiting: true,
        clientsClaim: true,
        // `version.json` NUNCA debe salir de la caché del SW: el sondeo de
        // auto-actualización necesita ver siempre la respuesta real de red.
        runtimeCaching: [
          { urlPattern: /\/api\/.*/i, handler: 'NetworkOnly' },
          { urlPattern: /\/version\.json(\?.*)?$/i, handler: 'NetworkOnly' },
        ],
      },
    }),
  ],
  define: {
    __BUILD_ID__: JSON.stringify(BUILD_ID),
  },
  server: {
    port: 5273,
  },
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: ['./tests/setup.js'],
    // Mismo ajuste que admin-eca: el `localStorage` experimental de Node
    // 20+ puede pisar al de jsdom según orden de carga.
    poolOptions: {
      forks: { execArgv: ['--no-experimental-webstorage'] },
      threads: { execArgv: ['--no-experimental-webstorage'] },
    },
  },
})
