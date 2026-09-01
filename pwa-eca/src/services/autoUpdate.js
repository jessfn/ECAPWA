// pwa-eca — auto-actualización sin recarga manual.
//
// Pedido explícito: "cada vez que se haga una deployada debe actualizarse
// inmediatamente la app aunque no se refresque o recargue el navegador".
//
// **Bug real encontrado y corregido en producción**: `registerType:
// 'autoUpdate'` hace que el cliente (`virtual:pwa-register`) recargue solo
// cuando el service worker nuevo pasa a estado `activated` — pero Workbox
// NUNCA activa un SW nuevo automáticamente a menos que el propio SW llame
// `self.skipWaiting()`, y eso solo pasa si se configura
// `skipWaiting: true` (+ `clientsClaim: true`) en las opciones de Workbox
// (`vite.config.js`). Sin eso, el SW nuevo se quedaba en estado
// "esperando" (`waiting`) para siempre — confirmado en el navegador con
// `registration.waiting` no nulo, incluso tras varios despliegues y
// recargas seguidas: la pestaña seguía sirviendo el `index.html`/JS del
// SW viejo indefinidamente, sin importar cuántas veces recargara.
//
// Con `skipWaiting`+`clientsClaim` ya en `vite.config.js`, el SW nuevo se
// activa solo apenas se instala, y `registerSW()` recarga la pestaña sola
// en cuanto eso ocurre (evento `activated`). Lo único que falta aquí es
// forzar el chequeo de actualización cada cierto tiempo (el navegador lo
// hace solo, pero mucho más espaciado) — para eso sirve el sondeo de
// `version.json` (siempre `NetworkOnly`, ver `vite.config.js`).
//
// No requiere ninguna acción del usuario ni un botón de "Actualizar".
import { registerSW } from 'virtual:pwa-register'

const INTERVALO_SONDEO_MS = 30_000

export function iniciarAutoActualizacion() {
  registerSW({ immediate: true })

  setInterval(async () => {
    try {
      const respuesta = await fetch(`/version.json?t=${Date.now()}`, { cache: 'no-store' })
      if (!respuesta.ok) return
      const { buildId } = await respuesta.json()
      if (!buildId || buildId === __BUILD_ID__) return

      if ('serviceWorker' in navigator) {
        const registro = await navigator.serviceWorker.getRegistration()
        if (registro) {
          // Fuerza el chequeo ya; el SW nuevo se instala y se activa solo
          // (`skipWaiting`), y eso dispara la recarga automática de
          // `registerSW()` de arriba — no hace falta recargar a mano aquí.
          await registro.update().catch(() => {})
          return
        }
      }
      // Sin service worker disponible (o deshabilitado): recargar directo.
      window.location.reload()
    } catch {
      // Sin red: no hacer nada, se reintenta en el próximo ciclo. Nunca
      // debe interrumpir al técnico por un sondeo fallido.
    }
  }, INTERVALO_SONDEO_MS)
}
