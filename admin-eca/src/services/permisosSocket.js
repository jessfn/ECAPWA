// admin-eca — cliente del WebSocket de avisos de permisos (ECA-021 v2).
//
// El servidor nunca manda los permisos nuevos en el mensaje (evitaría
// duplicar la lógica de resolución de permisos en el cliente) — solo avisa
// "algo cambió"; acá se responde pidiendo `GET /auth/me` de nuevo, la misma
// fuente de verdad que ya usa el login. Reconexión con backoff porque un
// móvil en campo pierde señal seguido; el watcher de `App.vue` es quien de
// verdad saca al usuario de una vista que perdió, esto solo dispara el
// refresco de `auth.permisos`.
import { useAuthStore } from '../stores/auth'

let socket = null
let intentoReconexion = null
let espera = 1000
let cerradoIntencionalmente = false

function urlSocket(token) {
  const base = import.meta.env.VITE_API_URL || ''
  const wsBase = base.replace(/^http/i, 'ws').replace(/\/$/, '')
  return `${wsBase}/ws/permisos?token=${encodeURIComponent(token)}`
}

export function conectarSocketPermisos() {
  const auth = useAuthStore()
  if (!auth.estaAutenticado || !auth.accessToken) return
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return

  cerradoIntencionalmente = false
  socket = new WebSocket(urlSocket(auth.accessToken))

  socket.onopen = () => {
    espera = 1000
  }

  socket.onmessage = (evento) => {
    try {
      const mensaje = JSON.parse(evento.data)
      if (mensaje?.tipo === 'permisos_cambiados') {
        auth.cargarPerfil().catch(() => {})
      }
    } catch {
      // Mensaje no-JSON: se ignora, no es del contrato esperado.
    }
  }

  socket.onclose = () => {
    socket = null
    if (cerradoIntencionalmente) return
    const auth2 = useAuthStore()
    if (!auth2.estaAutenticado) return
    clearTimeout(intentoReconexion)
    intentoReconexion = setTimeout(conectarSocketPermisos, espera)
    espera = Math.min(espera * 2, 30000)
  }

  socket.onerror = () => {
    socket?.close()
  }
}

export function desconectarSocketPermisos() {
  cerradoIntencionalmente = true
  clearTimeout(intentoReconexion)
  socket?.close()
  socket = null
}
