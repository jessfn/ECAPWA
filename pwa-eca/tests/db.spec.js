// pwa-eca — pruebas del esquema IndexedDB (ECA-016).
import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'
import { abrirBD, NOMBRE_BD, VERSION_BD, _reiniciarBDParaPruebas } from '../src/services/db'

beforeEach(async () => {
  await _reiniciarBDParaPruebas()
  await new Promise((resolve, reject) => {
    const peticion = indexedDB.deleteDatabase(NOMBRE_BD)
    peticion.onsuccess = () => resolve()
    peticion.onerror = () => reject(peticion.error)
    peticion.onblocked = () => resolve()
  })
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
