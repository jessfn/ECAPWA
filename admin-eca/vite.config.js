import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// admin-eca — configuración base (ECA-001) + entorno de pruebas (ECA-005)
// + auto-actualización sin recarga manual (pedido explícito: "cada vez
// que se haga una deployada debe actualizarse inmediatamente la app aunque
// no se refresque el navegador").
// ECA-002 dejó anotado que había que definir un entorno Node moderno antes
// de trabajar en serio en los frontends (el scaffold original de ECA-001
// se hizo en una máquina con Node 16.13.2, con Vite 4 pinneado). Esta
// máquina ya tiene Node 20+, así que aquí se sube a Vite 5.
//
// `BUILD_ID` se inyecta como `__BUILD_ID__` y se escribe en
// `dist/version.json`; `src/services/autoUpdate.js` sondea ese archivo y
// recarga sola la pestaña en cuanto detecta un build distinto.
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
  ],
  define: {
    __BUILD_ID__: JSON.stringify(BUILD_ID),
  },
  server: {
    port: 5274,
  },
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: ['./tests/setup.js'],
    // Node 20.25+/22+ trae su propio `localStorage` global experimental que
    // choca con el de jsdom (ver `tests/setup.js`). Desactivarlo en los
    // workers de prueba es más confiable que solo el parche en setup.js.
    poolOptions: {
      forks: { execArgv: ['--no-experimental-webstorage'] },
      threads: { execArgv: ['--no-experimental-webstorage'] },
    },
  },
})
