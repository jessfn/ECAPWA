// pwa-eca — pruebas del esquema IndexedDB (ECA-016 + ECA-021).
import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'
import { abrirBD, nombreBDPara, NOMBRE_BD, VERSION_BD, _reiniciarBDParaPruebas } from '../src/services/db'
import { guardarSesionLocal, limpiarSesionLocal } from '../src/services/sesionLocal'
import { encolar } from '../src/services/outbox'

async function borrarBD(nombre) {
  await new Promise((resolve, reject) => {
    const peticion = indexedDB.deleteDatabase(nombre)
    peticion.onsuccess = () => resolve()
    peticion.onerror = () => reject(peticion.error)
    peticion.onblocked = () => resolve()
  })
}

beforeEach(async () => {
  localStorage.clear()
  await _reiniciarBDParaPruebas()
  await borrarBD(NOMBRE_BD)
  await borrarBD(nombreBDPara(1))
  await borrarBD(nombreBDPara(2))
})

describe('abrirBD', () => {
  it('crea todos los object stores esperados', async () => {
    const db = await abrirBD()

    expect([...db.objectStoreNames].sort()).toEqual(
      ['catalogos', 'ecas', 'meta', 'outbox_actividades', 'outbox_evidencias', 'outbox_jornadas'].sort(),
    )
    expect(db.version).toBe(VERSION_BD)
  })

  it('outbox_evidencias tiene el índice por_actividad', async () => {
    const db = await abrirBD()
    const tx = db.transaction('outbox_evidencias', 'readonly')
    expect([...tx.store.indexNames]).toContain('por_actividad')
  })

  it('reutiliza la misma conexión entre llamadas', async () => {
    const a = await abrirBD()
    const b = await abrirBD()
    expect(a).toBe(b)
  })
})

// Regresión real reportada en producción: en el mismo dispositivo, si la
// Cuenta A inicia su jornada y luego se entra con la Cuenta B, la Cuenta B
// veía "ya iniciaste jornada" — el outbox era una sola base compartida
// para TODAS las cuentas del navegador, sin importar quién estuviera
// logueado.
describe('aislamiento del outbox por cuenta', () => {
  it('cada usuario logueado usa una base IndexedDB distinta', async () => {
    guardarSesionLocal({ usuario: { id: 1 }, permisos: [] })
    const dbA = await abrirBD()

    guardarSesionLocal({ usuario: { id: 2 }, permisos: [] })
    const dbB = await abrirBD()

    expect(dbA.name).not.toBe(dbB.name)
  })

  it('la jornada encolada por la Cuenta A no aparece para la Cuenta B', async () => {
    guardarSesionLocal({ usuario: { id: 1 }, permisos: [] })
    await encolar('outbox_jornadas', { uuid: 'jornada-de-A', inicio_en: new Date().toISOString() })

    guardarSesionLocal({ usuario: { id: 2 }, permisos: [] })
    const db = await abrirBD()
    const jornadasDeB = await db.getAll('outbox_jornadas')

    expect(jornadasDeB).toHaveLength(0)
  })

  it('sin sesión local (invitado) usa la base genérica, igual que antes', async () => {
    limpiarSesionLocal()
    const db = await abrirBD()
    expect(db.name).toBe(NOMBRE_BD)
  })

  // Regresión sobre el primer intento de arreglo: migrar "lo que hubiera"
  // de la base compartida hacia CADA cuenta nueva que abriera su base por
  // primera vez terminaba heredando el outbox entero (incluida una
  // jornada ya iniciada) a cualquier cuenta, sin importar de quién fueran
  // esos registros — la misma contaminación que se quería resolver, solo
  // que trasladada. Ahora una base de usuario nueva SIEMPRE arranca
  // vacía, sin importar qué haya en la base legado compartida.
  it('una cuenta nueva NUNCA hereda lo que haya en la base legado compartida', async () => {
    const dbLegado = await abrirBD()
    await dbLegado.put('outbox_jornadas', { uuid: 'jornada-de-otra-cuenta', inicio_en: new Date().toISOString() })
    await _reiniciarBDParaPruebas()

    guardarSesionLocal({ usuario: { id: 1 }, permisos: [] })
    const db = await abrirBD()
    const jornadas = await db.getAll('outbox_jornadas')

    expect(jornadas).toHaveLength(0)
  })
})
