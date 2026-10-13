// pwa-eca — WebSocket de avisos en tiempo real (notificaciones).
//
// El servidor solo manda `{tipo: "notificaciones_cambiaron"}` (sin contenido)
// y un `ping` cada 25 s. Al recibir el aviso se vuelve a pedir la bandeja.
// Reconexión con backoff (un móvil en campo pierde señal seguido); un vigilante
// cierra el socket si pasan 70 s sin ningún mensaje (conexión "colgada").
import { useAuthStore } from '../stores/auth'
import { useNotificacionesStore } from '../stores/notificaciones'
import { tokenExpirado } from './jwt'

let socket = null
let reconexion = null
let vigilante = null
let espera = 1000
let detenido = true

function urlSocket(token) {
  const base = import.meta.env.VITE_API_URL || ''
  const wsBase = base.replace(/^http/i, 'ws').replace(/\/$/, '')
  return `${wsBase}/ws/permisos?token=${encodeURIComponent(token)}`
}

function armarVigilante() {
  clearTimeout(vigilante)
  vigilante = setTimeout(() => socket?.close(), 70000)
}

function programarReconexion() {
  if (detenido) return
  clearTimeout(reconexion)
  reconexion = setTimeout(conectarSocketNotificaciones, espera)
  espera = Math.min(espera * 2, 30000)
}

export async function conectarSocketNotificaciones() {
  detenido = false
  const auth = useAuthStore()
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
  if (!navigator.onLine) return programarReconexion()

  try {
    if (!auth.accessToken || tokenExpirado(auth.accessToken)) await auth.refrescar()
  } catch {
    return programarReconexion()
  }
  if (!auth.accessToken || detenido) return

  const store = useNotificacionesStore()
  socket = new WebSocket(urlSocket(auth.accessToken))
  socket.onopen = () => {
    espera = 1000
    armarVigilante()
    store.cargar() // ponerse al día con lo que pasó mientras no había socket
  }
  socket.onmessage = (evento) => {
    armarVigilante()
    try {
      const mensaje = JSON.parse(evento.data)
      if (mensaje?.tipo === 'notificaciones_cambiaron') store.cargar()
    } catch {
      // mensaje fuera de contrato: se ignora
    }
  }
  socket.onclose = () => {
    clearTimeout(vigilante)
    socket = null
    programarReconexion()
  }
  socket.onerror = () => socket?.close()
}

export function desconectarSocketNotificaciones() {
  detenido = true
  clearTimeout(reconexion)
  clearTimeout(vigilante)
  socket?.close()
  socket = null
}
