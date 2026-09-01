// pwa-eca — pruebas del store `jornada` (ECA-012 + ECA-016).
// Desde ECA-016 escribe en el outbox local, no llama a la API.
import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
import { NOMBRE_BD, _reiniciarBDParaPruebas } from '../src/services/db'
import { useJornadaStore } from '../src/stores/jornada'

beforeEach(async () => {
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
