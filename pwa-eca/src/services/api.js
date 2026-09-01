// pwa-eca — cliente HTTP (ECA-011), mismo patrón que admin-eca (ECA-005).
//
// Interceptor de request: adjunta `Authorization` si hay sesión.
// Interceptor de response: ante un 401 (y solo uno) intenta refrescar el
// token y reintenta la petición original; si el refresh también falla,
// cierra la sesión de servidor — pero **no** borra la sesión local offline
// (§2.2): un `access_token` vencido sin red no debe cerrarle la app al
// técnico en campo. Eso lo decide el guard de rutas, no este interceptor.
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

let storeAuth = null
// Import diferido: `stores/auth.js` usa este mismo cliente para hacer sus
// peticiones, así que importarlo aquí arriba crearía un ciclo.
export async function obtenerStoreAuth() {
  if (!storeAuth) {
    const { useAuthStore } = await import('../stores/auth')
    storeAuth = useAuthStore()
  }
  return storeAuth
}

export function _reiniciarStoreAuthParaPruebas() {
  storeAuth = null
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('eca_tecnico_access_token')
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function manejarErrorDeRespuesta(error) {
  const peticionOriginal = error.config
  const esLogin = peticionOriginal?.url?.includes('/auth/login')
  const esRefresh = peticionOriginal?.url?.includes('/auth/refresh')

  if (error.response?.status !== 401 || esLogin || esRefresh || peticionOriginal._reintentada) {
    return Promise.reject(error)
  }
  peticionOriginal._reintentada = true

  const auth = await obtenerStoreAuth()
  try {
    await auth.refrescar()
  } catch (errorRefresh) {
    // Solo se cierra la sesión de *servidor*: la sesión local offline
    // (si hay una vigente) sobrevive, para no expulsar de la app a un
    // técnico que se quedó sin red mientras trabajaba (§2.2).
    auth.cerrarSesionDeServidor()
    return Promise.reject(errorRefresh)
  }

  peticionOriginal.headers.Authorization = `Bearer ${auth.accessToken}`
  return api(peticionOriginal)
}

api.interceptors.response.use((respuesta) => respuesta, manejarErrorDeRespuesta)
