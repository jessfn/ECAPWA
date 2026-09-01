// admin-eca — cliente HTTP (ECA-005).
//
// Interceptor de request: adjunta `Authorization` si hay sesión.
// Interceptor de response: ante un 401 (y solo uno) intenta refrescar el
// token y reintenta la petición original; si el refresh también falla,
// cierra sesión (04_ARQUITECTURA_OBJETIVO.md §2: "Axios con interceptor...
// refresca token en 401").
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

let storeAuth = null
// Import diferido: `stores/auth.js` usa este mismo cliente para hacer sus
// peticiones, así que importarlo aquí arriba crearía un ciclo. `useAuthStore`
// solo se resuelve la primera vez que un interceptor lo necesita de verdad
// (para entonces Pinia ya está instalado).
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
  const token = localStorage.getItem('eca_admin_access_token')
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Exportada por separado (en vez de un closure anónimo dentro de `.use(...)`)
// para poder probarla directamente en `tests/` sin depender de la mecánica
// interna de interceptores de Axios.
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
    auth.cerrarSesionLocal()
    return Promise.reject(errorRefresh)
  }

  peticionOriginal.headers.Authorization = `Bearer ${auth.accessToken}`
  return api(peticionOriginal)
}

api.interceptors.response.use((respuesta) => respuesta, manejarErrorDeRespuesta)
