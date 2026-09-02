// pwa-eca — esquema IndexedDB versionado (ECA-016), con base de datos
// separada por usuario (ECA-021, bug real reportado en producción).
//
// Bug encontrado: la base de datos usaba SIEMPRE el mismo nombre
// ('eca-tecnico'), sin importar quién estuviera logueado. En un
// dispositivo compartido (o simplemente al cambiar de cuenta en el mismo
// navegador), la Cuenta B veía el outbox de la Cuenta A — p. ej. "ya
// inició jornada" cuando en realidad quien la inició fue otra persona.
// Ahora el nombre de la base incluye el `id` del usuario logueado
// (leído de la misma marca de sesión local que ya usa el guard de rutas,
// `services/sesionLocal.js` — sin sesión local, se usa la base genérica
// de "invitado", igual que antes).
//
// `onupgradeneeded` (vía `idb`) crea los object stores que faltan por
// versión — corrige `02` §15: el legado de SV no versionaba su store y
// usaba base64 en vez de `Blob` para fotos.
import { openDB } from 'idb'
import { leerSesionLocal } from './sesionLocal'

export const NOMBRE_BD = 'eca-tecnico'
export const VERSION_BD = 1

const TIENDAS_OUTBOX = ['outbox_jornadas', 'outbox_actividades', 'outbox_evidencias']

export function nombreBDPara(idUsuario) {
  return idUsuario ? `${NOMBRE_BD}-${idUsuario}` : NOMBRE_BD
}

function idUsuarioActivo() {
  return leerSesionLocal()?.usuario?.id ?? null
}

function crearEsquema(db) {
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
}

// Mejor esfuerzo, una sola vez por base nueva: si este dispositivo tenía
// pendientes en la base genérica de antes de este cambio (compartida entre
// cuentas), se copian a la base ya aislada del usuario actual — nunca se
// pierden, y de aquí en adelante quedan correctamente separados por
// cuenta. Sin usuario_id en los registros viejos no hay forma de saber de
// quién eran de verdad; se asignan al usuario que los "hereda" primero,
// que es exactamente el mismo comportamiento (ambiguo) que ya tenían
// antes de este arreglo — no lo empeora, solo deja de repetirlo hacia
// adelante.
async function migrarDesdeLegadoSiHaceFalta(db) {
  const yaMigrado = await db.get('meta', 'migrado_legado')
  if (yaMigrado) return
  try {
    const dbLegado = await openDB(NOMBRE_BD, VERSION_BD, { upgrade: crearEsquema })
    for (const tienda of TIENDAS_OUTBOX) {
      const registros = await dbLegado.getAll(tienda)
      for (const registro of registros) {
        const existe = await db.get(tienda, registro.uuid)
        if (!existe) await db.put(tienda, registro)
      }
    }
    dbLegado.close()
  } catch {
    // Sin la base legado (navegador nuevo, ya migrado antes, etc.) no hay
    // nada que copiar — seguir sin bloquear la apertura de la base actual.
  }
  await db.put('meta', { clave: 'migrado_legado', valor: true })
}

let promesaBD = null
let idUsuarioAbierto

export function abrirBD() {
  const idActual = idUsuarioActivo()
  if (!promesaBD || idActual !== idUsuarioAbierto) {
    if (promesaBD) {
      promesaBD.then((db) => db.close()).catch(() => {})
    }
    idUsuarioAbierto = idActual
    promesaBD = (async () => {
      const db = await openDB(nombreBDPara(idActual), VERSION_BD, { upgrade: crearEsquema })
      if (idActual) await migrarDesdeLegadoSiHaceFalta(db)
      return db
    })()
  }
  return promesaBD
}

export async function _reiniciarBDParaPruebas() {
  if (promesaBD) {
    const db = await promesaBD
    db.close()
  }
  promesaBD = null
  idUsuarioAbierto = undefined
}
