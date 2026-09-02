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

// Distingue "el usuario negó el permiso" de "no hubo señal todavía": son
// causas muy distintas (una no se arregla reintentando, la otra sí) y la
// UI necesita saberlo para pedir explícitamente activar el permiso en el
// dispositivo en vez de solo decir "sin señal".
function unIntento(timeoutMs) {
  return new Promise((resolve) => {
    if (!('geolocation' in navigator)) {
      resolve({ ok: false, permisoDenegado: false })
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          ok: true,
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        }),
      // Código 1 = PERMISSION_DENIED en la spec de `GeolocationPositionError`
      // (no se usa `err.PERMISSION_DENIED`: un error genérico sin esa
      // propiedad estática daría `undefined === undefined` → falso positivo).
      (err) => resolve({ ok: false, permisoDenegado: err?.code === 1 }),
      { timeout: timeoutMs, maximumAge: 0, enableHighAccuracy: true },
    )
  })
}

// Salvavidas independiente del `timeout` de la propia API: verificado en
// pruebas reales que, mientras el navegador tiene pendiente el diálogo de
// permiso de ubicación (el usuario aún no responde "Permitir"/"Bloquear"),
// `getCurrentPosition` puede quedarse sin llamar a ninguno de los dos
// callbacks — ni éxito ni error — así que su propio `timeout` nunca llega a
// dispararse y la captura se cuelga indefinidamente. Un `setTimeout` de JS
// sí corre siempre (no depende de que el navegador resuelva el diálogo),
// así que garantiza que cada intento avance en un tiempo acotado.
function conLimiteDeTiempo(promesa, ms) {
  return Promise.race([promesa, new Promise((resolve) => setTimeout(() => resolve({ ok: false, permisoDenegado: false }), ms))])
}

// Más intentos (antes 3) y con más tiempo cada uno (antes 6s): pedido
// explícito de que la ubicación sea "exacta" — el GPS de un celular tarda
// unos segundos en afinar tras el primer intento (frío), así que solo el
// mejor de varias lecturas (menor `accuracy`, en metros) se queda.
export async function capturarGps({ intentos = 4, timeoutMs = 8000 } = {}) {
  if (!('geolocation' in navigator)) {
    return { estado_gps: 'SIN_GPS' }
  }

  let mejor = null
  let permisoDenegado = false
  for (let i = 0; i < intentos; i += 1) {
    const resultado = await conLimiteDeTiempo(unIntento(timeoutMs), timeoutMs + 1000)
    if (resultado.ok && (!mejor || resultado.accuracy < mejor.accuracy)) {
      mejor = resultado
    }
    if (!resultado.ok && resultado.permisoDenegado) {
      permisoDenegado = true
      break // reintentar no sirve de nada si el navegador ya lo negó
    }
  }

  if (!mejor) {
    return { estado_gps: 'SIN_GPS', permiso_denegado: permisoDenegado }
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
