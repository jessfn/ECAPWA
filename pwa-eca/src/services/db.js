// pwa-eca — esquema IndexedDB versionado (ECA-016).
//
// `onupgradeneeded` (vía `idb`) crea los object stores que faltan por
// versión — corrige `02` §15: el legado de SV no versionaba su store y
// usaba base64 en vez de `Blob` para fotos.
import { openDB } from 'idb'

export const NOMBRE_BD = 'eca-tecnico'
export const VERSION_BD = 1

let promesaBD = null

export function abrirBD() {
  if (!promesaBD) {
    promesaBD = openDB(NOMBRE_BD, VERSION_BD, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('outbox_jornadas')) {
          db.createObjectStore('outbox_jornadas', { keyPath: 'uuid' })
        }
        if (!db.objectStoreNames.contains('outbox_actividades')) {
          db.createObjectStore('outbox_actividades', { keyPath: 'uuid' })
        }
        if (!db.objectStoreNames.contains('outbox_evidencias')) {
          const tienda = db.createObjectStore('outbox_evidencias', { keyPath: 'uuid' })
          tienda.createIndex('por_actividad', 'actividad_uuid')
        }
        if (!db.objectStoreNames.contains('catalogos')) {
          db.createObjectStore('catalogos', { keyPath: 'clave' })
        }
        if (!db.objectStoreNames.contains('ecas')) {
          db.createObjectStore('ecas', { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains('meta')) {
          db.createObjectStore('meta', { keyPath: 'clave' })
        }
      },
    })
  }
  return promesaBD
}

export async function _reiniciarBDParaPruebas() {
  if (promesaBD) {
    const db = await promesaBD
    db.close()
  }
  promesaBD = null
}
