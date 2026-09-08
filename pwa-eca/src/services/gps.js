// pwa-eca — captura de GPS (ECA-014 + ECA-021 + rediseño de velocidad).
//
// Objetivo (pedido explícito): extraer la ubicación MUY RÁPIDO y de forma
// OBLIGATORIA. El flujo anterior podía tardar hasta 30s (esperaba 8s tras
// cada mejora de precisión y forzaba `maximumAge:0`, descartando cualquier
// lectura en caché). Este flujo prioriza la rapidez sin dejar de exigir
// coordenadas reales:
//
//   1. Se acepta una lectura RECIENTE en caché del dispositivo
//      (`maximumAge`), que suele devolverse al instante.
//   2. Un primer `getCurrentPosition` de baja precisión (red/celda) trae
//      un fix rápido en paralelo, mientras un `watchPosition` de alta
//      precisión lo va refinando.
//   3. Se resuelve APENAS se alcanza una lectura "buena" (bajo el umbral).
//   4. Si a los `objetivoMs` (2.5s) todavía no hay una "buena", se entrega
//      la MEJOR que se tenga (marcada `GPS_IMPRECISO`) — sigue siendo una
//      coordenada real y satisface el requisito de ubicación obligatoria.
//   5. Tope duro corto (`timeoutMs`, 10s) como salvavidas: entrega lo mejor
//      que haya, o `SIN_GPS` solo si el dispositivo no dio NINGUNA lectura
//      (permiso denegado / sin sensor) — nunca se inventa una posición.
import { obtenerParametro } from './parametrosConfigService'

const UMBRAL_POR_DEFECTO_M = 30

export function capturarGps({ timeoutMs = 10000, objetivoMs = 2500, maxEdadMs = 60000 } = {}) {
  // El umbral de "precisión válida" se resuelve en paralelo (está cacheado
  // tras la primera vez): NO se bloquea la captura esperándolo. Hasta que
  // llegue se usa el valor por defecto.
  let umbral = UMBRAL_POR_DEFECTO_M
  obtenerParametro('gps.precision_valida_maxima_m', { porDefecto: UMBRAL_POR_DEFECTO_M })
    .then((v) => {
      if (typeof v === 'number' && v > 0) umbral = v
    })
    .catch(() => {})

  return new Promise((resolve) => {
    if (!('geolocation' in navigator)) {
      resolve({ estado_gps: 'SIN_GPS' })
      return
    }

    let resuelto = false
    let mejor = null
    let watchId = null
    let temporizadorTope = null
    let temporizadorObjetivo = null

    function limpiar() {
      if (watchId != null) navigator.geolocation.clearWatch(watchId)
      clearTimeout(temporizadorTope)
      clearTimeout(temporizadorObjetivo)
    }

    function resolverConMejor(permisoDenegado = false) {
      if (resuelto) return
      resuelto = true
      limpiar()

      if (!mejor) {
        resolve({ estado_gps: 'SIN_GPS', ...(permisoDenegado ? { permiso_denegado: true } : {}) })
        return
      }
      resolve({
        latitud: mejor.coords.latitude,
        longitud: mejor.coords.longitude,
        precision_gps_m: mejor.coords.accuracy,
        estado_gps: mejor.coords.accuracy <= umbral ? 'CON_GPS' : 'GPS_IMPRECISO',
      })
    }

    function considerar(posicion) {
      if (resuelto) return
      if (!mejor || posicion.coords.accuracy < mejor.coords.accuracy) {
        mejor = posicion
      }
      // Apenas llega una lectura suficientemente precisa, se entrega ya —
      // sin esperar más (esto es lo que antes tardaba).
      if (mejor.coords.accuracy <= umbral) {
        resolverConMejor()
      }
    }

    // (5) Tope duro: pase lo que pase, en `timeoutMs` se entrega lo mejor.
    temporizadorTope = setTimeout(() => resolverConMejor(), timeoutMs)
    // (4) Objetivo rápido: a los `objetivoMs`, si ya hay ALGUNA lectura, se
    // entrega esa (imprecisa) en vez de seguir esperando una mejor.
    temporizadorObjetivo = setTimeout(() => {
      if (mejor) resolverConMejor()
    }, objetivoMs)

    // (2)+(3) Refinamiento en alta precisión: mejora el fix hasta alcanzar
    // el umbral (o hasta que el objetivo/tope resuelvan). Se registra
    // PRIMERO para que `watchId` ya exista si un fix llega de inmediato y
    // la limpieza cancele bien el watch.
    try {
      watchId = navigator.geolocation.watchPosition(
        considerar,
        (error) => {
          if (error?.code === 1) resolverConMejor(true)
          // Otros errores (sin señal momentánea): se sigue esperando; el
          // objetivo/tope garantizan una respuesta.
        },
        { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: maxEdadMs },
      )
    } catch {
      // se sigue con el getCurrentPosition de abajo
    }

    // (1) Fix inicial veloz: acepta caché reciente y no exige alta
    // precisión, así el primer callback llega casi de inmediato.
    try {
      navigator.geolocation.getCurrentPosition(
        considerar,
        (error) => {
          if (error?.code === 1) resolverConMejor(true) // permiso denegado
        },
        { enableHighAccuracy: false, timeout: timeoutMs, maximumAge: maxEdadMs },
      )
    } catch {
      // sin getCurrentPosition (o falló): el watch de arriba dirige.
    }
  })
}
