// pwa-eca — captura de GPS (ECA-014 + ECA-021).
//
// Mismo flujo que pwasuper (`geoLocationService.js`: `watchPosition`,
// quedarse con la mejor lectura, resolver apenas se alcanza buena
// precisión o al agotar el tiempo de espera) — pedido explícito de
// alinear el comportamiento del botón/permiso de ubicación con el que ya
// funciona bien ahí. Tiempos generosos (30s tope / 8s de espera extra por
// cada mejora de precisión) igual que el primer intento de pwasuper, para
// darle al GPS real el mismo margen de conseguir una lectura buena antes
// de conformarse con una imprecisa.
//
// Una diferencia deliberada y CONFIRMADA con el usuario: aquí **nunca se
// inventa una posición** (`03` §20, `02` §13) — pwasuper cae a una
// ubicación de respaldo fija (CDMX) si todo falla; este proyecto siempre
// prefiere devolver la lectura real más aproximada que haya conseguido
// (o `SIN_GPS` si de plano no hubo ninguna) antes que guardar una
// coordenada falsa en el registro de jornada.
import { obtenerParametro } from './parametrosConfigService'

const UMBRAL_POR_DEFECTO_M = 30

// Salvavidas independiente del `timeout` de la propia API: verificado en
// pruebas reales que, mientras el navegador tiene pendiente el diálogo de
// permiso de ubicación (el usuario aún no responde "Permitir"/"Bloquear"),
// `watchPosition`/`getCurrentPosition` pueden no llamar a NINGÚN callback
// — ni éxito ni error — así que el `timeout` de la API nunca llega a
// dispararse y la captura se cuelga indefinidamente. Un `setTimeout` de JS
// sí corre siempre (no depende de que el navegador resuelva el diálogo).
export function capturarGps({ timeoutMs = 30000, maxEsperaMejorPrecisionMs = 8000 } = {}) {
  return new Promise((resolve) => {
    if (!('geolocation' in navigator)) {
      resolve({ estado_gps: 'SIN_GPS' })
      return
    }

    let resuelto = false
    let mejor = null
    let watchId = null
    let temporizadorTope = null
    let temporizadorEspera = null

    function limpiar() {
      if (watchId != null) navigator.geolocation.clearWatch(watchId)
      clearTimeout(temporizadorTope)
      clearTimeout(temporizadorEspera)
    }

    async function resolverConMejor(permisoDenegado = false) {
      if (resuelto) return
      resuelto = true
      limpiar()

      if (!mejor) {
        resolve({ estado_gps: 'SIN_GPS', ...(permisoDenegado ? { permiso_denegado: true } : {}) })
        return
      }

      const umbral = await obtenerParametro('gps.precision_valida_maxima_m', {
        porDefecto: UMBRAL_POR_DEFECTO_M,
      })
      resolve({
        latitud: mejor.coords.latitude,
        longitud: mejor.coords.longitude,
        precision_gps_m: mejor.coords.accuracy,
        estado_gps: mejor.coords.accuracy <= umbral ? 'CON_GPS' : 'GPS_IMPRECISO',
      })
    }

    // Tope absoluto: pase lo que pase (colgado, sin señal, permiso
    // pendiente sin resolver), en `timeoutMs` se entrega lo mejor que
    // haya (o SIN_GPS si no hubo nada).
    temporizadorTope = setTimeout(() => resolverConMejor(), timeoutMs)

    try {
      watchId = navigator.geolocation.watchPosition(
        (posicion) => {
          if (resuelto) return
          if (!mejor || posicion.coords.accuracy < mejor.coords.accuracy) {
            mejor = posicion
            // Cada vez que llega una lectura mejor, se espera un poco más
            // por si aún mejora — pero sin reiniciar el tope absoluto de
            // arriba, así nunca se alarga indefinidamente.
            clearTimeout(temporizadorEspera)
            temporizadorEspera = setTimeout(() => resolverConMejor(), maxEsperaMejorPrecisionMs)
          }
        },
        // Código 1 = PERMISSION_DENIED en la spec de
        // `GeolocationPositionError` (no `err.PERMISSION_DENIED`: un error
        // genérico sin esa propiedad estática daría un falso positivo).
        (error) => {
          if (error?.code === 1) {
            resolverConMejor(true)
          }
          // Otros errores (sin señal momentánea, timeout de un intento):
          // se sigue esperando — `watchPosition` puede recuperarse solo,
          // y el tope absoluto de arriba igual garantiza una respuesta.
        },
        { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 0 },
      )
    } catch {
      resolverConMejor()
    }
  })
}
