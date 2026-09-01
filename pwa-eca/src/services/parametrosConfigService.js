// pwa-eca — lectura de parámetros de configuración operativos (ECA-014).
// Caché en memoria por clave: no cambian dentro de una sesión de la app.
import { api } from './api'

const cache = new Map()

export async function obtenerParametro(clave, { porDefecto = null } = {}) {
  if (cache.has(clave)) return cache.get(clave)
  try {
    const { data } = await api.get(`/parametros-config/${clave}`)
    cache.set(clave, data.valor)
    return data.valor
  } catch {
    // Sin red o parámetro no sembrado: se sigue con el valor por defecto,
    // nunca bloquea el flujo (mismo espíritu que el GPS: mejor esfuerzo).
    return porDefecto
  }
}

export function _reiniciarParametrosCacheParaPruebas() {
  cache.clear()
}
