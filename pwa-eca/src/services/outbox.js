// pwa-eca — outbox offline (ECA-016).
//
// `estado_local` es exclusivamente del dispositivo (§2.3 de
// `04_ARQUITECTURA_OBJETIVO.md`): nunca se envía al servidor ni se
// confunde con un estado de negocio de `jornadas`/`actividades`. El motor
// de sincronización real (que lee este outbox y empuja al backend) llega
// en ECA-017 — aquí solo se implementa encolar/listar/marcar/purgar.
import { abrirBD } from './db'

export const TIENDAS = ['outbox_jornadas', 'outbox_actividades', 'outbox_evidencias']
const ESTADOS_PENDIENTES = new Set(['PENDIENTE', 'SINCRONIZANDO', 'RECHAZADO'])

export async function encolar(tienda, objeto) {
  const db = await abrirBD()
  const registro = {
    ...objeto,
    estado_local: 'PENDIENTE',
    intentos: 0,
    ultimo_error: null,
    encolado_en: new Date().toISOString(),
  }
  await db.put(tienda, registro)
  return registro
}

// Escribe un registro tal cual, sin los efectos de `encolar` (que siempre
// marca PENDIENTE) — para hidratar el outbox con la verdad del servidor
// (ver `stores/jornada.js: cargarHoy`), no para una edición local nueva.
export async function reemplazar(tienda, registro) {
  const db = await abrirBD()
  await db.put(tienda, registro)
  return registro
}

export async function actualizar(tienda, uuid, cambios) {
  const db = await abrirBD()
  const registro = await db.get(tienda, uuid)
  if (!registro) return null
  const actualizado = { ...registro, ...cambios, actualizado_en: new Date().toISOString() }
  await db.put(tienda, actualizado)
  return actualizado
}

export async function marcarEstado(tienda, uuid, estadoLocal, { ultimoError = null } = {}) {
  const db = await abrirBD()
  const registro = await db.get(tienda, uuid)
  if (!registro) return null
  registro.estado_local = estadoLocal
  registro.ultimo_error = ultimoError
  if (estadoLocal === 'SINCRONIZANDO' || estadoLocal === 'RECHAZADO') {
    registro.intentos = (registro.intentos || 0) + 1
  }
  await db.put(tienda, registro)
  return registro
}

export async function obtener(tienda, uuid) {
  const db = await abrirBD()
  return db.get(tienda, uuid)
}

export async function listar(tienda) {
  const db = await abrirBD()
  return db.getAll(tienda)
}

export async function listarDeActividad(actividadUuid) {
  const db = await abrirBD()
  return db.getAllFromIndex('outbox_evidencias', 'por_actividad', actividadUuid)
}

export async function listarTodo() {
  const [jornadas, actividades, evidencias] = await Promise.all([
    listar('outbox_jornadas'),
    listar('outbox_actividades'),
    listar('outbox_evidencias'),
  ])
  return [
    ...jornadas.map((r) => ({ ...r, tipo: 'jornada' })),
    ...actividades.map((r) => ({ ...r, tipo: 'actividad' })),
    ...evidencias.map((r) => ({ ...r, tipo: 'evidencia' })),
  ]
}

export async function contarPendientes() {
  const todo = await listarTodo()
  return todo.filter((r) => ESTADOS_PENDIENTES.has(r.estado_local)).length
}

export async function purgar(tienda, diasRetencion = 30) {
  const db = await abrirBD()
  const todos = await db.getAll(tienda)
  const limiteMs = Date.now() - diasRetencion * 24 * 60 * 60 * 1000
  let eliminados = 0
  for (const registro of todos) {
    const encoladoEnMs = new Date(registro.encolado_en).getTime()
    if (registro.estado_local === 'SINCRONIZADO' && encoladoEnMs < limiteMs) {
      await db.delete(tienda, registro.uuid)
      eliminados += 1
    }
  }
  return eliminados
}
