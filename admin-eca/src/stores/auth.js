// admin-eca — store de sesión (ECA-005).
//
// Única fuente de verdad de la sesión del panel: token de acceso, refresh
// token, usuario y permisos efectivos (los permisos vienen de `GET
// /auth/me`, nunca se calculan en el cliente — la autorización real la
// impone siempre el backend, esto es solo para mostrar/ocultar UI).
import { defineStore } from 'pinia'
import { api } from '../services/api'
import { tokenExpirado } from '../services/jwt'

const CLAVE_ACCESS_TOKEN = 'eca_admin_access_token'
const CLAVE_REFRESH_TOKEN = 'eca_admin_refresh_token'
const CLAVE_USUARIO = 'eca_admin_usuario'
const CLAVE_PERMISOS = 'eca_admin_permisos'

function leerJson(clave, porDefecto) {
  try {
    const crudo = localStorage.getItem(clave)
    return crudo ? JSON.parse(crudo) : porDefecto
  } catch {
    return porDefecto
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem(CLAVE_ACCESS_TOKEN) || null,
    refreshToken: localStorage.getItem(CLAVE_REFRESH_TOKEN) || null,
    usuario: leerJson(CLAVE_USUARIO, null),
    permisos: leerJson(CLAVE_PERMISOS, []),
  }),

  getters: {
    // No basta con que exista el token (`02`/`04` §2: el guard viejo de SV
    // solo miraba `localStorage.user`): también debe seguir vigente.
    estaAutenticado: (state) => Boolean(state.accessToken) && !tokenExpirado(state.accessToken),
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
      this._guardarTokens(data.access_token, data.refresh_token)
      await this.cargarPerfil()
    },

    async cargarPerfil() {
      const { data } = await api.get('/auth/me')
      this.usuario = data.usuario
      this.permisos = data.permisos
      localStorage.setItem(CLAVE_USUARIO, JSON.stringify(this.usuario))
      localStorage.setItem(CLAVE_PERMISOS, JSON.stringify(this.permisos))
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
        // Best-effort: si el backend no responde, igual limpiamos la sesión local.
        await api.post('/auth/logout', { refresh_token: this.refreshToken }).catch(() => {})
      }
      this.cerrarSesionLocal()
    },

    cerrarSesionLocal() {
      this.accessToken = null
      this.refreshToken = null
      this.usuario = null
      this.permisos = []
      localStorage.removeItem(CLAVE_ACCESS_TOKEN)
      localStorage.removeItem(CLAVE_REFRESH_TOKEN)
      localStorage.removeItem(CLAVE_USUARIO)
      localStorage.removeItem(CLAVE_PERMISOS)
    },
  },
})
