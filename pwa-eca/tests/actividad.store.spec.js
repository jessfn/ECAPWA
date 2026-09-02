// pwa-eca — pruebas del store `actividad` (ECA-013 + ECA-016).
// Desde ECA-016 escribe en el outbox local, no llama a la API.
import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'
import { NOMBRE_BD, _reiniciarBDParaPruebas } from '../src/services/db'
import { listar } from '../src/services/outbox'
import { useActividadStore } from '../src/stores/actividad'

beforeEach(async () => {
  setActivePinia(createPinia())
  await _reiniciarBDParaPruebas()
  await new Promise((resolve, reject) => {
    const peticion = indexedDB.deleteDatabase(NOMBRE_BD)
    peticion.onsuccess = () => resolve()
    peticion.onerror = () => reject(peticion.error)
    peticion.onblocked = () => resolve()
  })
})

const DATOS = {
  jornadaUuid: 'j1',
  ecaId: 5,
  modalidadId: 1,
  tipoActividadId: 2,
  temaId: null,
  subtemaId: null,
  sistemaProductivoId: null,
  descripcion: 'Se hizo una visita.',
  resultado: null,
  numParticipantes: null,
  requiereSeguimiento: false,
  fechaProximoSeguimiento: null,
  gps: null,
}

describe('useActividadStore.crear', () => {
  it('encola la actividad localmente con las claves que espera el backend', async () => {
    const actividad = useActividadStore()

    const registro = await actividad.crear(DATOS)

    expect(registro.jornada_uuid).toBe('j1')
    expect(registro.eca_id).toBe(5)
    expect(registro.descripcion).toBe('Se hizo una visita.')
    expect(registro.uuid).toBeTruthy()
    expect(registro.estado_local).toBe('PENDIENTE')
    expect(actividad.error).toBe('')

    const enOutbox = await listar('outbox_actividades')
    expect(enOutbox).toHaveLength(1)
  })

  // Regresión real reportada en producción: registrar una actividad CON
  // ubicación fallaba siempre con "No se pudo guardar la actividad
  // localmente" — un `ref()` de Vue al que se le asigna un objeto (aquí,
  // el GPS capturado en `NuevaActividadView.vue`) queda envuelto en un
  // Proxy reactivo; pasarlo tal cual a `IDBObjectStore.put` revienta con
  // `DataCloneError`, atrapado en silencio por el catch de `crear`. Mismo
  // bug que ya se había corregido para `stores/jornada.js`, pero no para
  // actividades.
  it('crear acepta un gps reactivo (Proxy de Vue) sin reventar IndexedDB', async () => {
    const actividad = useActividadStore()
    const gpsReactivo = reactive({ estado_gps: 'CON_GPS', latitud: 19.4, longitud: -99.1, precision_gps_m: 12 })

    const registro = await actividad.crear({ ...DATOS, gps: gpsReactivo })

    expect(actividad.error).toBe('')
    expect(registro.gps.estado_gps).toBe('CON_GPS')
  })
})

describe('useActividadStore.encolarEvidencias', () => {
  it('encola cada foto con el `orden` correcto, como Blob', async () => {
    const actividad = useActividadStore()
    const fotos = [
      { id: 'a', archivo: new Blob(['x']) },
      { id: 'b', archivo: new Blob(['y']) },
    ]

    const errores = await actividad.encolarEvidencias('act-uuid', fotos, null)

    expect(errores).toEqual([])
    const enOutbox = await listar('outbox_evidencias')
    expect(enOutbox).toHaveLength(2)
    expect(enOutbox.map((e) => e.orden).sort()).toEqual([1, 2])
    expect(enOutbox.every((e) => e.actividad_uuid === 'act-uuid')).toBe(true)
    // No se verifica el contenido del Blob tras el roundtrip: el
    // structured-clone de `fake-indexeddb` bajo jsdom no reconoce el
    // `Blob` de jsdom como nativo y lo vacía — una limitación conocida del
    // entorno de prueba, no del código (en un navegador real no ocurre).
    // Que `encolar` reciba y guarde `foto.archivo` tal cual (sin
    // convertirlo a base64 en ningún punto) se verifica por inspección del
    // código de `stores/actividad.js`.
  })

  it('acepta un gps reactivo (Proxy de Vue) sin reventar IndexedDB', async () => {
    const actividad = useActividadStore()
    const gpsReactivo = reactive({ estado_gps: 'CON_GPS', latitud: 19.4, longitud: -99.1, precision_gps_m: 12 })
    const fotos = [{ id: 'a', archivo: new Blob(['x']) }]

    const errores = await actividad.encolarEvidencias('act-uuid', fotos, gpsReactivo)

    expect(errores).toEqual([])
  })
})
