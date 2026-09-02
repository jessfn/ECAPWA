// pwa-eca — store de sesión del técnico (ECA-011).
//
// Dos nociones de sesión conviven a propósito (§2.2):
// - **Sesión de servidor**: `access_token` vigente (lo normal, con red).
// - **Sesión local offline**: marca guardada tras el último login+bootstrap
//   exitosos, vigente durante `VITE_OFFLINE_SESSION_DIAS` (DP-1) aunque el
//   `access_token` ya haya caducado y no haya red — ver `sesionLocal.js`.
// El guard de rutas (`router/index.js`) exige **una u otra**, no solo la
// primera.
import { defineStore, getActivePinia } from 'pinia'
import { api } from '../services/api'
import { tokenExpirado } from '../services/jwt'
import { guardarSesionLocal, sesionLocalVigente, leerSesionLocal } from '../services/sesionLocal'
import { ejecutarBootstrap } from '../services/bootstrap'

const CLAVE_ACCESS_TOKEN = 'eca_tecnico_access_token'
const CLAVE_REFRESH_TOKEN = 'eca_tecnico_refresh_token'

// Defensa en profundidad (ECA-021): además de que cada cuenta ya usa su
// propia base IndexedDB (`services/db.js`), los demás stores de Pinia
// (jornada, ecas, catalogos, actividad, outbox) son singletons en memoria
// que NO se destruyen entre un logout y el login siguiente en la misma
// pestaña — a diferencia de pwasuper, que fuerza una recarga completa de
// página en el logout (`window.location.href = '/login'`) y así borra
// todo el estado JS sin pedirlo explícitamente. Aquí no se recarga la
// página (mejor UX), así que hay que vaciar a mano cualquier store con
// datos de la cuenta anterior — evita que se alcance a pintar por un
// instante (o, si algún flujo nuevo olvida recargar, indefinidamente) el
// dato viejo de la Cuenta A mientras el store de la Cuenta B todavía está
// resolviendo su propia carga. Se resuelve genérico (iterando los stores
// ya activos) para no crear un import circular con jornada.js, que ya
// importa este mismo archivo.
function reiniciarStoresDeCuenta() {
  const pinia = getActivePinia()
  if (!pinia) return
  for (const store of pinia._s.values()) {
    if (store.$id !== 'auth') store.$reset()
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem(CLAVE_ACCESS_TOKEN) || null,
    refreshToken: localStorage.getItem(CLAVE_REFRESH_TOKEN) || null,
    usuario: leerSesionLocal()?.usuario || null,
    permisos: leerSesionLocal()?.permisos || [],
  }),

  getters: {
    sesionServidorValida: (state) => Boolean(state.accessToken) && !tokenExpirado(state.accessToken),
    sesionLocalVigente: () => sesionLocalVigente(),
    // El guard de rutas usa esto: server O local, exactamente como pide
    // el criterio de aceptación del ticket.
    estaAutenticado(state) {
      return this.sesionServidorValida || this.sesionLocalVigente
    },
    tienePermiso: (state) => (clave) => state.permisos.includes(clave),
  },

  actions: {
    _guardarTokens(accessToken, refreshToken) {
      this.accessToken = accessToken
      this.refreshToken = refreshToken
      localStorage.setItem(CLAVE_ACCESS_TOKEN, accessToken)
      localStorage.setItem(CLAVE_REFRESH_TOKEN, refreshToken)
    },

    async login(correo, contrasena) {
      const { data } = await api.post('/auth/login', { correo, contrasena })
      // Antes de tocar nada de la cuenta nueva: fuera cualquier dato en
      // memoria que hubiera quedado de una cuenta distinta en esta misma
      // pestaña (ver comentario de `reiniciarStoresDeCuenta`).
      reiniciarStoresDeCuenta()
      this._guardarTokens(data.access_token, data.refresh_token)
      await this.cargarPerfilYBootstrap()
      // Bootstrap de datos offline (ECA-018): catálogos + ECA del técnico.
      // Mejor esfuerzo — si falla, la app sigue funcionando y lo reintenta
      // el propio store de catálogos/ECA la próxima vez que se usen.
      ejecutarBootstrap().catch(() => {})
    },

    // "Bootstrap": `GET /auth/me` con red, y a partir de esa respuesta se
    // renueva la marca de sesión local offline (§2.2) — es lo que habilita
    // después abrir/navegar/capturar sin red aunque el token expire.
    async cargarPerfilYBootstrap() {
      const { data } = await api.get('/auth/me')
      this.usuario = data.usuario
      this.permisos = data.permisos
      guardarSesionLocal({ usuario: this.usuario, permisos: this.permisos })
    },

    async refrescar() {
      if (!this.refreshToken) {
        throw new Error('No hay refresh token con qué renovar la sesión.')
      }
      const { data } = await api.post('/auth/refresh', { refresh_token: this.refreshToken })
      this._guardarTokens(data.access_token, data.refresh_token)
      return data.access_token
    },

    async logout() {
      if (this.refreshToken) {
        await api.post('/auth/logout', { refresh_token: this.refreshToken }).catch(() => {})
      }
      this.cerrarSesionDeServidor()
      // El logout explícito del técnico sí borra también la sesión local:
      // a diferencia de una expiración pasiva, aquí hay intención clara de
      // salir de la app.
      localStorage.removeItem('eca_tecnico_sesion_local')
      this.usuario = null
      this.permisos = []
      reiniciarStoresDeCuenta()
    },

    // Cierra solo la sesión de *servidor* (tokens). Nunca toca la sesión
    // local offline ni el outbox — usada por el interceptor de refresh
    // fallido y por expiración pasiva, donde SÍ debe seguir funcionando
    // el modo offline si la marca local sigue vigente.
    cerrarSesionDeServidor() {
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem(CLAVE_ACCESS_TOKEN)
      localStorage.removeItem(CLAVE_REFRESH_TOKEN)
    },
  },
})
