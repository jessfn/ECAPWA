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
  ecaNombre: 'ECA de prueba',
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
    expect(registro.eca_id).toBe(null)
    expect(registro.eca_nombre).toBe('ECA de prueba')
    expect(registro.descripcion).toBe('Se hizo una visita.')
    expect(registro.uuid).toBeTruthy()
    expect(registro.estado_local).toBe('PENDIENTE')
    expect(actividad.error).toBe('')

    const enOutbox = await listar('outbox_actividades')
    expect(enOutbox).toHaveLength(1)
  })

  // Regresión real: el modal de confirmación mostraba "ya se sincronizó"
  // (o, por una carrera aparte, "sin señal") sin importar lo que en verdad
  // le pasó a ESTA actividad — `ultimoSync.ok` solo confirma que la
  // petición viajó, no que esta actividad puntual fue aceptada. Ahora
  // `crear()` vuelve a leer el registro del outbox después de sincronizar
  // y expone su estado real en `estadoActividad`.
  it('ultimoSync trae el estado real del registro, no solo el agregado del lote', async () => {
    const actividad = useActividadStore()

    const registro = await actividad.crear(DATOS)

    expect(actividad.ultimoSync).toHaveProperty('estadoActividad')
    // Sin servidor real en la prueba, la sincronización no puede completarse
    // — el registro se queda como se encoló (nunca se pierde ni se inventa
    // un estado que no ocurrió de verdad).
    expect(actividad.ultimoSync.estadoActividad).toBe(registro.estado_local)
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

// La captura real entrega un File/Blob; el código lee sus BYTES con
// `.arrayBuffer()` para guardarlos como ArrayBuffer durable (fiable en iOS).
// jsdom no implementa `Blob.arrayBuffer()` de forma consistente, así que se
// usa un doble ligero con los tres accesos que usa el código: `arrayBuffer`,
// `type` y `name`.
function fotoFalsa(id, texto) {
  const bytes = new TextEncoder().encode(texto)
  return {
    id,
    archivo: {
      type: 'image/jpeg',
      name: `${id}.jpg`,
      arrayBuffer: async () => bytes.buffer,
    },
  }
}

describe('useActividadStore.encolarEvidencias', () => {
  it('encola cada foto con el `orden` correcto, guardando los bytes como ArrayBuffer', async () => {
    const actividad = useActividadStore()
    const fotos = [fotoFalsa('a', 'x'), fotoFalsa('b', 'y')]

    const errores = await actividad.encolarEvidencias('act-uuid', fotos, null)

    expect(errores).toEqual([])
    const enOutbox = await listar('outbox_evidencias')
    expect(enOutbox).toHaveLength(2)
    expect(enOutbox.map((e) => e.orden).sort()).toEqual([1, 2])
    expect(enOutbox.every((e) => e.actividad_uuid === 'act-uuid')).toBe(true)
    // Se guardan los bytes + mime + nombre, NO un Blob: es lo que sobrevive
    // de forma fiable a IndexedDB en iOS (el Blob directo se desalojaba y la
    // foto se perdía). El Blob se reconstruye al subir. (No se comprueba
    // `instanceof ArrayBuffer` tras el roundtrip: el structured-clone de
    // fake-indexeddb bajo jsdom cambia la identidad del tipo — limitación
    // del entorno, no del código; se verifica que el campo quedó guardado y
    // que YA NO se guarda un `archivo`/Blob.)
    expect(enOutbox.every((e) => e.archivo_buffer != null)).toBe(true)
    expect(enOutbox.every((e) => e.archivo === undefined)).toBe(true)
    expect(enOutbox.every((e) => e.archivo_mime === 'image/jpeg')).toBe(true)
    expect(enOutbox.every((e) => typeof e.archivo_nombre === 'string')).toBe(true)
  })

  it('acepta un gps reactivo (Proxy de Vue) sin reventar IndexedDB', async () => {
    const actividad = useActividadStore()
    const gpsReactivo = reactive({ estado_gps: 'CON_GPS', latitud: 19.4, longitud: -99.1, precision_gps_m: 12 })
    const fotos = [fotoFalsa('a', 'x')]

    const errores = await actividad.encolarEvidencias('act-uuid', fotos, gpsReactivo)

    expect(errores).toEqual([])
  })
})
