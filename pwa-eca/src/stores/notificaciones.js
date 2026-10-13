// pwa-eca — store de notificaciones del técnico (bandeja, contador, avisos).
//
// La fuente de verdad es `GET /notificaciones/mias`. El WebSocket y el Web
// Push solo AVISAN "hay algo nuevo"; este store vuelve a pedir la bandeja
// (tolerante a avisos perdidos: también se pide al abrir, al volver a primer
// plano y al recuperar red). Se guarda copia en localStorage por cuenta para
// poder leerlas sin conexión.
import { defineStore } from 'pinia'
import { api } from '../services/api'
import { useAuthStore } from './auth'

const MAX_TOASTS = 3

function claveCache() {
  const id = useAuthStore().usuario?.id
  return id ? `eca_tecnico_notif_${id}` : null
}

function leerCache() {
  try {
    const clave = claveCache()
    return clave ? JSON.parse(localStorage.getItem(clave) || 'null') : null
  } catch {
    return null
  }
}

function escribirCache(items, noLeidas) {
  try {
    const clave = claveCache()
    if (clave) localStorage.setItem(clave, JSON.stringify({ items, noLeidas }))
  } catch {
    // almacenamiento lleno o bloqueado: la bandeja sigue funcionando en memoria
  }
}

function actualizarInsignia(n) {
  try {
    if (n > 0) navigator.setAppBadge?.(n)
    else navigator.clearAppBadge?.()
  } catch {
    // Badging API no disponible: sin efecto
  }
}

export const useNotificacionesStore = defineStore('notificaciones', {
  state: () => ({
    items: [],
    noLeidas: 0,
    cargado: false,
    cargando: false,
    sinConexion: false,
    toasts: [],
    panelAbierto: false,
    detalleUuid: null,
  }),

  getters: {
    detalle: (state) => state.items.find((n) => n.uuid === state.detalleUuid) || null,
  },

  actions: {
    restaurarCache() {
      const cache = leerCache()
      if (cache && !this.cargado) {
        this.items = cache.items || []
        this.noLeidas = cache.noLeidas || 0
      }
    },

    async cargar() {
      if (this.cargando) return
      this.cargando = true
      try {
        const { data } = await api.get('/notificaciones/mias', { params: { limite: 50 } })
        const previas = new Set(this.items.map((n) => n.uuid))
        const nuevas = this.cargado
          ? data.notificaciones.filter((n) => !n.leida && !previas.has(n.uuid))
          : []
        this.items = data.notificaciones
        this.noLeidas = data.no_leidas
        this.cargado = true
        this.sinConexion = false
        escribirCache(this.items, this.noLeidas)
        actualizarInsignia(this.noLeidas)
        if (!this.panelAbierto) {
          // Más nuevas primero; se muestran como máximo MAX_TOASTS.
          for (const n of nuevas.slice(0, MAX_TOASTS)) this.toasts.push(n)
        }
      } catch {
        this.sinConexion = true
      } finally {
        this.cargando = false
      }
    },

    cerrarToast(uuid) {
      this.toasts = this.toasts.filter((t) => t.uuid !== uuid)
    },

    abrirPanel(uuid = null) {
      this.detalleUuid = uuid
      this.panelAbierto = true
      this.toasts = []
      if (uuid) this.marcarLeida(uuid)
    },

    cerrarPanel() {
      this.panelAbierto = false
      this.detalleUuid = null
    },

    async marcarLeida(uuid) {
      const n = this.items.find((x) => x.uuid === uuid)
      if (!n || n.leida) return
      n.leida = true
      this.noLeidas = Math.max(0, this.noLeidas - 1)
      escribirCache(this.items, this.noLeidas)
      actualizarInsignia(this.noLeidas)
      try {
        await api.post(`/notificaciones/${uuid}/leida`)
      } catch {
        // Sin red: se reconcilia en la siguiente carga.
      }
    },

    async marcarTodasLeidas() {
      this.items.forEach((n) => (n.leida = true))
      this.noLeidas = 0
      escribirCache(this.items, 0)
      actualizarInsignia(0)
      try {
        await api.post('/notificaciones/leer-todas')
      } catch {
        // idem
      }
    },
  },
})
