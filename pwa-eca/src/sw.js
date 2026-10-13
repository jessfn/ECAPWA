// pwa-eca — service worker propio (estrategia `injectManifest`).
//
// Hace lo mismo que el SW que generaba Workbox (precache de la app +
// fallback de navegación a /index.html + auto-actualización con
// `skipWaiting`/`clientsClaim`, ver `vite.config.js` y `autoUpdate.js`) y
// añade las notificaciones Web Push: `push` (mostrar el aviso) y
// `notificationclick` (abrir la app en esa notificación).
//
// A propósito NO hay ruta para `/api` ni `/version.json`: sin ruta el
// navegador va directo a la red (equivale al `NetworkOnly` anterior), así el
// sondeo de auto-actualización siempre ve la respuesta real.
import { clientsClaim } from 'workbox-core'
import { precacheAndRoute, cleanupOutdatedCaches, createHandlerBoundToURL } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'

self.skipWaiting()
clientsClaim()
cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)
registerRoute(new NavigationRoute(createHandlerBoundToURL('/index.html')))

const TITULOS = { INFO: 'Aviso', EXITO: 'Éxito', ALERTA: 'Alerta', URGENTE: 'Urgente' }

self.addEventListener('push', (evento) => {
  let datos = {}
  try {
    datos = evento.data ? evento.data.json() : {}
  } catch {
    datos = { titulo: 'Nueva notificación', cuerpo: evento.data?.text() || '' }
  }
  // Siempre se muestra algo: iOS revoca la suscripción si un push no
  // produce una notificación visible.
  const titulo = datos.titulo || 'Nueva notificación'
  const opciones = {
    body: datos.cuerpo || TITULOS[datos.tipo] || '',
    icon: '/icon-192.png',
    badge: '/badge-96.png',
    tag: datos.uuid || undefined,
    renotify: Boolean(datos.uuid),
    timestamp: Date.now(),
    vibrate: [90, 50, 90],
    requireInteraction: datos.tipo === 'URGENTE',
    data: { uuid: datos.uuid || null, url: datos.url || null },
  }
  if (datos.imagen) opciones.image = datos.imagen
  evento.waitUntil(self.registration.showNotification(titulo, opciones))
})

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close()
  const { uuid } = evento.notification.data || {}
  evento.waitUntil(
    (async () => {
      const ventanas = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      const propia = ventanas.find((v) => new URL(v.url).origin === self.location.origin)
      if (propia) {
        await propia.focus()
        propia.postMessage({ tipo: 'abrir_notificacion', uuid })
        return
      }
      await self.clients.openWindow(uuid ? `/?notif=${uuid}` : '/')
    })(),
  )
})
