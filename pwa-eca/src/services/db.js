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

// Bug real de producción (ECA-021): la primera versión de este arreglo
// migraba —de la base genérica compartida `eca-tecnico` hacia CADA base
// nueva de usuario que se abriera por primera vez— todo lo que hubiera
// quedado ahí. Eso "heredaba" el outbox entero (incluida una jornada ya
// iniciada) a CUALQUIER cuenta que iniciara sesión por primera vez en ese
// dispositivo, sin importar de quién fueran esos registros en realidad —
// exactamente la misma contaminación entre cuentas que se quería
// resolver, solo que trasladada a la base legado en vez de a la
// compartida. Sin `usuario_id` en los registros viejos no hay forma
// confiable de saber a quién pertenecían, así que ya NO se migra nada:
// cada base nueva de usuario arranca siempre vacía. Los pendientes que
// hubiera en la base legado de antes de este arreglo se pierden (costo
// aceptable, único, ya pagado) en vez de seguir contaminando cuentas
// nuevas indefinidamente.

let promesaBD = null
let idUsuarioAbierto

export function abrirBD() {
  const idActual = idUsuarioActivo()
  if (!promesaBD || idActual !== idUsuarioAbierto) {
    if (promesaBD) {
      promesaBD.then((db) => db.close()).catch(() => {})
    }
    idUsuarioAbierto = idActual
    promesaBD = openDB(nombreBDPara(idActual), VERSION_BD, { upgrade: crearEsquema })
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
