// pwa-eca — pruebas del store `jornada` (ECA-012 + ECA-016).
// Desde ECA-016 escribe en el outbox local, no llama a la API.
import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
import { NOMBRE_BD, _reiniciarBDParaPruebas } from '../src/services/db'
import { useJornadaStore } from '../src/stores/jornada'
import { useAuthStore } from '../src/stores/auth'
import { obtenerJornadaDeHoy } from '../src/services/jornadasService'

vi.mock('../src/services/jornadasService', () => ({
  obtenerJornadaDeHoy: vi.fn(),
}))

// `cargarHoy` ahora asegura sesión de servidor (sesionServidorValida)
// antes de llamar a `obtenerJornadaDeHoy` — sin un access_token vigente en
// localStorage, se salta la hidratación de raíz (evita el 401 predecible
// contra un token ya vencido). Los tests de hidratación necesitan uno.
function crearJwt(payload) {
  const base64url = (obj) => btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${base64url({ alg: 'none' })}.${base64url(payload)}.firma`
}
const TOKEN_VIGENTE = crearJwt({ sub: '1', exp: Date.now() / 1000 + 900 })

beforeEach(async () => {
  localStorage.clear()
  setActivePinia(createPinia())
  await _reiniciarBDParaPruebas()
  await new Promise((resolve, reject) => {
    const peticion = indexedDB.deleteDatabase(NOMBRE_BD)
    peticion.onsuccess = () => resolve()
    peticion.onerror = () => reject(peticion.error)
    peticion.onblocked = () => resolve()
  })
  global.navigator.geolocation = {
    getCurrentPosition: (_ok, err) => err(new Error('sin permiso')),
  }
  vi.mocked(obtenerJornadaDeHoy).mockReset().mockResolvedValue(null)
})

describe('useJornadaStore', () => {
  it('iniciar encola la jornada localmente (nunca llama a la red)', async () => {
    const jornada = useJornadaStore()

    await jornada.iniciar()

    expect(jornada.actual.estado_local).toBe('PENDIENTE')
    expect(jornada.actual.fin_en).toBeNull()
    expect(jornada.error).toBe('')
  })

  it('iniciar funciona aunque el GPS falle (nunca bloquea)', async () => {
    const jornada = useJornadaStore()

    await jornada.iniciar()

    expect(jornada.actual.gps_inicio.estado_gps).toBe('SIN_GPS')
  })

  it('cargarHoy recupera del outbox la jornada ya encolada', async () => {
    const primera = useJornadaStore()
    await primera.iniciar()

    const segunda = useJornadaStore()
    await segunda.cargarHoy()

    expect(segunda.actual.uuid).toBe(primera.actual.uuid)
  })

  // Regresión: un técnico que inicia jornada en el celular y luego abre
  // la app en la laptop veía "Aún no inicias tu jornada" ahí — el outbox
  // local de la laptop nunca supo que ya existía. `cargarHoy` ahora
  // contrasta con `GET /jornadas/me/hoy` y, si el servidor ya tiene una
  // jornada que este dispositivo desconoce, la adopta localmente.
  it('cargarHoy hidrata desde el servidor una jornada iniciada en otro dispositivo', async () => {
    useAuthStore().accessToken = TOKEN_VIGENTE
    vi.mocked(obtenerJornadaDeHoy).mockResolvedValue({
      uuid: 'servidor-uuid-1',
      inicio_en: new Date().toISOString(),
      latitud_inicio: 19.4,
      longitud_inicio: -99.1,
      precision_gps_inicio_m: 10,
      estado_gps_inicio: 'CON_GPS',
      fin_en: null,
      latitud_fin: null,
      longitud_fin: null,
      precision_gps_fin_m: null,
      estado_gps_fin: null,
    })

    const jornada = useJornadaStore()
    await jornada.cargarHoy()

    expect(jornada.actual.uuid).toBe('servidor-uuid-1')
    expect(jornada.abierta).toBe(true)
    expect(jornada.actual.estado_local).toBe('SINCRONIZADO')
  })

  // Regresión complementaria: si la jornada se INICIÓ en este mismo
  // dispositivo (ya está en el outbox) pero se CERRÓ desde otro, este
  // dispositivo debe enterarse del cierre y no quedar "abierta" para
  // siempre bloqueando Actividades sin razón.
  it('cargarHoy adopta el cierre hecho en otro dispositivo', async () => {
    const jornada = useJornadaStore()
    await jornada.iniciar()
    const uuid = jornada.actual.uuid
    const inicioEn = jornada.actual.inicio_en

    useAuthStore().accessToken = TOKEN_VIGENTE
    vi.mocked(obtenerJornadaDeHoy).mockResolvedValue({
      uuid,
      inicio_en: inicioEn,
      latitud_inicio: null,
      longitud_inicio: null,
      precision_gps_inicio_m: null,
      estado_gps_inicio: 'SIN_GPS',
      fin_en: new Date().toISOString(),
      latitud_fin: null,
      longitud_fin: null,
      precision_gps_fin_m: null,
      estado_gps_fin: 'SIN_GPS',
    })

    await jornada.cargarHoy()

    expect(jornada.abierta).toBe(false)
    expect(jornada.actual.fin_en).toBeTruthy()
  })

  // Regresión real reportada en producción: la consola mostraba un 401
  // Unauthorized de `GET /jornadas/me/hoy` cada vez que se abría Inicio con
  // el access_token ya vencido (y sin refresh_token con qué renovarlo) —
  // `cargarHoy` disparaba la llamada sin fijarse primero si había sesión de
  // servidor. Sin token en absoluto (ni refresh), ni siquiera debe
  // intentarlo.
  it('cargarHoy no llama al servidor sin sesión de servidor ni refresh token', async () => {
    const jornada = useJornadaStore()

    await jornada.cargarHoy()

    expect(obtenerJornadaDeHoy).not.toHaveBeenCalled()
    expect(jornada.error).toBe('')
  })

  it('cerrar actualiza el registro local sin perder el inicio', async () => {
    const jornada = useJornadaStore()
    await jornada.iniciar()
    const inicioEn = jornada.actual.inicio_en

    await jornada.cerrar()

    expect(jornada.actual.fin_en).toBeTruthy()
    expect(jornada.actual.inicio_en).toBe(inicioEn)
    expect(jornada.abierta).toBe(false)
  })

  // Regresión: `JornadaAccionModal` guarda el GPS capturado en un `ref()`,
  // que Vue vuelve reactivo (Proxy) al asignarle un objeto. Pasar ese Proxy
  // directo a `iniciar`/`cerrar` llega hasta `IDBObjectStore.put` y revienta
  // con `DataCloneError: could not be cloned` — silencioso para el usuario
  // porque el store lo atrapa y solo muestra "No se pudo iniciar/terminar
  // la jornada.". El arreglo real vive en el componente (copia plana antes
  // de emitir), pero este test fija el contrato: un `gpsPrevio` reactivo no
  // debe tumbar la escritura en IndexedDB.
  it('iniciar acepta un gps reactivo (Proxy de Vue) sin reventar IndexedDB', async () => {
    const jornada = useJornadaStore()
    const gpsReactivo = reactive({ estado_gps: 'SIN_GPS' })

    await jornada.iniciar(gpsReactivo)

    expect(jornada.error).toBe('')
    expect(jornada.actual.gps_inicio.estado_gps).toBe('SIN_GPS')
  })

  it('cerrar acepta un gps reactivo (Proxy de Vue) sin reventar IndexedDB', async () => {
    const jornada = useJornadaStore()
    await jornada.iniciar()
    const gpsReactivo = reactive({ estado_gps: 'CON_GPS', latitud: 19.4, longitud: -99.1, precision_gps_m: 12 })

    await jornada.cerrar(gpsReactivo)

    expect(jornada.error).toBe('')
    expect(jornada.actual.gps_fin.estado_gps).toBe('CON_GPS')
  })
})
