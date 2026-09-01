// pwa-eca — captura de GPS (ECA-014).
//
// Multi-intento, **sin ubicación por defecto** (`03` §20, `02` §13): si no
// hay permiso, no hay señal, o se agotan los intentos, se devuelve
// `estado_gps: 'SIN_GPS'` sin coordenadas — nunca se inventa una posición.
// El umbral de "precisión válida" viene de
// `parametros_config.gps.precision_valida_maxima_m` (configurable sin
// desplegar código); si no se puede leer (sin red, parámetro no sembrado),
// se usa 30 m como valor de respaldo razonable.
import { obtenerParametro } from './parametrosConfigService'

const UMBRAL_POR_DEFECTO_M = 30

function unIntento(timeoutMs) {
  return new Promise((resolve) => {
    if (!('geolocation' in navigator)) {
      resolve(null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        }),
      () => resolve(null),
      { timeout: timeoutMs, maximumAge: 0, enableHighAccuracy: true },
    )
  })
}

export async function capturarGps({ intentos = 3, timeoutMs = 6000 } = {}) {
  if (!('geolocation' in navigator)) {
    return { estado_gps: 'SIN_GPS' }
  }

  let mejor = null
  for (let i = 0; i < intentos; i += 1) {
    const resultado = await unIntento(timeoutMs)
    if (resultado && (!mejor || resultado.accuracy < mejor.accuracy)) {
      mejor = resultado
    }
  }

  if (!mejor) {
    return { estado_gps: 'SIN_GPS' }
  }

  const umbral = await obtenerParametro('gps.precision_valida_maxima_m', {
    porDefecto: UMBRAL_POR_DEFECTO_M,
  })

  return {
    latitud: mejor.lat,
    longitud: mejor.lon,
    precision_gps_m: mejor.accuracy,
    estado_gps: mejor.accuracy <= umbral ? 'CON_GPS' : 'GPS_IMPRECISO',
  }
}
