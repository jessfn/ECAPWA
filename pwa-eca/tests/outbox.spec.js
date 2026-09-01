// pwa-eca — pruebas del outbox offline (ECA-016).
import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach } from 'vitest'
import { NOMBRE_BD, _reiniciarBDParaPruebas } from '../src/services/db'
import {
  encolar,
  actualizar,
  marcarEstado,
  listar,
  listarTodo,
  contarPendientes,
  purgar,
} from '../src/services/outbox'

beforeEach(async () => {
  await _reiniciarBDParaPruebas()
  await new Promise((resolve, reject) => {
    const peticion = indexedDB.deleteDatabase(NOMBRE_BD)
    peticion.onsuccess = () => resolve()
    peticion.onerror = () => reject(peticion.error)
    peticion.onblocked = () => resolve()
  })
})

describe('outbox.encolar', () => {
  it('persiste el objeto con estado_local PENDIENTE', async () => {
    const registro = await encolar('outbox_jornadas', { uuid: 'j1', inicio_en: '2026-03-05T08:00:00Z' })

    expect(registro.estado_local).toBe('PENDIENTE')
    expect(registro.intentos).toBe(0)

    const todos = await listar('outbox_jornadas')
    expect(todos).toHaveLength(1)
    expect(todos[0].uuid).toBe('j1')
  })

  it('encolar no requiere red ni depende de ningún token', async () => {
    // No hay ningún mock de red/API en este archivo: si `encolar` llamara
    // a algo de eso, esta prueba fallaría por falta de ese mock.
    const registro = await encolar('outbox_actividades', { uuid: 'a1', descripcion: 'x' })
    expect(registro.uuid).toBe('a1')
  })
})

describe('outbox.actualizar', () => {
  it('fusiona cambios y conserva el resto del registro', async () => {
    await encolar('outbox_jornadas', { uuid: 'j1', inicio_en: '2026-03-05T08:00:00Z', fin_en: null })

    const actualizado = await actualizar('outbox_jornadas', 'j1', { fin_en: '2026-03-05T17:00:00Z' })

    expect(actualizado.fin_en).toBe('2026-03-05T17:00:00Z')
    expect(actualizado.inicio_en).toBe('2026-03-05T08:00:00Z') // no se perdió
  })

  it('devuelve null si el uuid no existe', async () => {
    const resultado = await actualizar('outbox_jornadas', 'no-existe', { fin_en: 'x' })
    expect(resultado).toBeNull()
  })
})

describe('outbox.marcarEstado', () => {
  it('incrementa intentos al marcar RECHAZADO', async () => {
    await encolar('outbox_actividades', { uuid: 'a1' })

    const primero = await marcarEstado('outbox_actividades', 'a1', 'RECHAZADO', { ultimoError: 'motivo' })
    const segundo = await marcarEstado('outbox_actividades', 'a1', 'RECHAZADO', { ultimoError: 'motivo' })

    expect(primero.intentos).toBe(1)
    expect(segundo.intentos).toBe(2)
    expect(segundo.ultimo_error).toBe('motivo')
  })

  it('SINCRONIZADO no incrementa intentos', async () => {
    await encolar('outbox_actividades', { uuid: 'a1' })
    const marcado = await marcarEstado('outbox_actividades', 'a1', 'SINCRONIZADO')
    expect(marcado.intentos).toBe(0)
  })
})

describe('outbox.contarPendientes / listarTodo', () => {
  it('cuenta pendientes y rechazados de las tres tiendas, no los sincronizados', async () => {
    await encolar('outbox_jornadas', { uuid: 'j1' })
    await encolar('outbox_actividades', { uuid: 'a1' })
    await encolar('outbox_evidencias', { uuid: 'e1', actividad_uuid: 'a1' })
    await marcarEstado('outbox_actividades', 'a1', 'SINCRONIZADO')

    const total = await contarPendientes()

    expect(total).toBe(2) // j1 y e1 siguen pendientes; a1 ya sincronizó
  })

  it('listarTodo etiqueta cada registro con su tipo', async () => {
    await encolar('outbox_jornadas', { uuid: 'j1' })
    await encolar('outbox_evidencias', { uuid: 'e1', actividad_uuid: 'a1' })

    const todo = await listarTodo()

    expect(todo.find((r) => r.uuid === 'j1').tipo).toBe('jornada')
    expect(todo.find((r) => r.uuid === 'e1').tipo).toBe('evidencia')
  })
})

describe('outbox.purgar', () => {
  it('elimina solo SINCRONIZADO con antigüedad mayor a dias_retencion', async () => {
    const db = await import('../src/services/db').then((m) => m.abrirBD())
    await db.put('outbox_jornadas', {
      uuid: 'viejo',
      estado_local: 'SINCRONIZADO',
      encolado_en: new Date(Date.now() - 40 * 24 * 60 * 60 * 1000).toISOString(),
    })
    await db.put('outbox_jornadas', {
      uuid: 'reciente',
      estado_local: 'SINCRONIZADO',
      encolado_en: new Date().toISOString(),
    })
    await db.put('outbox_jornadas', {
      uuid: 'pendiente-viejo',
      estado_local: 'PENDIENTE',
      encolado_en: new Date(Date.now() - 40 * 24 * 60 * 60 * 1000).toISOString(),
    })

    const eliminados = await purgar('outbox_jornadas', 30)

    expect(eliminados).toBe(1)
    const restantes = (await listar('outbox_jornadas')).map((r) => r.uuid).sort()
    expect(restantes).toEqual(['pendiente-viejo', 'reciente'])
  })
})
