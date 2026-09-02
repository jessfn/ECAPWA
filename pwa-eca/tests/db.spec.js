// pwa-eca — pruebas del esquema IndexedDB (ECA-016 + ECA-021).
import 'fake-indexeddb/auto'
import { openDB } from 'idb'
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
  await borrarBD(nombreBDPara(99))
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

  // Regresión CRÍTICA: dispositivos que ya se habían contaminado (base de
  // usuario en v1, con la jornada de otra cuenta adentro) MIENTRAS la
  // migración de la primera versión de este arreglo todavía existía en
  // producción, se quedaban con ese dato malo para siempre — quitar la
  // migración en el código nuevo no limpia bases que ya existían y ya
  // fueron contaminadas antes del deploy de ese código. Reportado de
  // nuevo por el usuario en su propio celular tras el primer fix. El
  // bump a VERSION_BD=2 fuerza `onupgradeneeded` (y la purga ahí dentro)
  // en CUALQUIER base v1 existente, contaminada o no, sin importar
  // cuándo se haya creado.
  it('una base v1 YA contaminada (de antes de este fix) se purga al abrirse en v2', async () => {
    // Simula el estado real de un celular afectado: la base de la Cuenta
    // B en la v1 vieja, con la jornada de la Cuenta A adentro (así quedó
    // el primer intento de arreglo antes de quitar la migración).
    const dbVieja = await openDB(nombreBDPara(99), 1, {
      upgrade(db) {
        db.createObjectStore('outbox_jornadas', { keyPath: 'uuid' })
        db.createObjectStore('outbox_actividades', { keyPath: 'uuid' })
        const tienda = db.createObjectStore('outbox_evidencias', { keyPath: 'uuid' })
        tienda.createIndex('por_actividad', 'actividad_uuid')
        db.createObjectStore('catalogos', { keyPath: 'clave' })
        db.createObjectStore('ecas', { keyPath: 'id' })
        db.createObjectStore('meta', { keyPath: 'clave' })
      },
    })
    await dbVieja.put('outbox_jornadas', { uuid: 'jornada-de-otra-cuenta-de-antes', inicio_en: new Date().toISOString() })
    await dbVieja.put('meta', { clave: 'migrado_legado', valor: true })
    dbVieja.close()

    guardarSesionLocal({ usuario: { id: 99 }, permisos: [] })
    const db = await abrirBD()
    const jornadas = await db.getAll('outbox_jornadas')

    expect(db.version).toBe(2)
    expect(jornadas).toHaveLength(0)
  })
})
