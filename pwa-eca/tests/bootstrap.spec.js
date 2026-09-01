// pwa-eca — pruebas de bootstrap/pull offline (ECA-018).
import 'fake-indexeddb/auto'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { NOMBRE_BD, _reiniciarBDParaPruebas } from '../src/services/db'

vi.mock('../src/services/api', () => ({
  api: { get: vi.fn() },
}))

import { api } from '../src/services/api'
import { ejecutarBootstrap, ejecutarPull, leerCatalogosLocal, leerEcasLocal, leerMetaBootstrap } from '../src/services/bootstrap'

beforeEach(async () => {
  vi.clearAllMocks()
  await _reiniciarBDParaPruebas()
  await new Promise((resolve, reject) => {
    const peticion = indexedDB.deleteDatabase(NOMBRE_BD)
    peticion.onsuccess = () => resolve()
    peticion.onerror = () => reject(peticion.error)
    peticion.onblocked = () => resolve()
  })
})

const RESPUESTA = {
  generado_en: '2026-03-05T08:00:00Z',
  catalogos: {
    modalidades: [{ id: 1, clave: 'CAMPO', nombre: 'Campo', orden: 0 }],
    tipos_actividad: [],
    temas: [],
    subtemas: [],
    sistemas_productivos: [],
  },
  geo: { estados: [{ id: 1, nombre: 'CDMX' }], municipios: [{ id: 1, estado_id: 1, nombre: 'M1' }] },
  ambito: [1],
  ecas: [{ eca_id: 10, eca_uuid: 'x', eca_nombre: 'ECA 1', municipio_id: 1, origen: 'AMBITO' }],
  config: { regla_disponibilidad: 'ASIGNADAS_LUEGO_AMBITO', gps_precision_maxima_m: 30, eca_max_offline: 1500, sesion_offline_dias: 30 },
  aviso: null,
}

describe('ejecutarBootstrap', () => {
  it('guarda catálogos, ecas y meta en IndexedDB', async () => {
    api.get.mockResolvedValueOnce({ data: RESPUESTA })

    await ejecutarBootstrap()

    const catalogos = await leerCatalogosLocal()
    expect(catalogos.modalidades).toEqual(RESPUESTA.catalogos.modalidades)

    const ecas = await leerEcasLocal()
    expect(ecas).toEqual([{ id: 10, eca_id: 10, eca_uuid: 'x', eca_nombre: 'ECA 1', municipio_id: 1, origen: 'AMBITO' }])

    const meta = await leerMetaBootstrap()
    expect(meta.generado_en).toBe(RESPUESTA.generado_en)
  })

  it('reemplaza el conjunto de ecas anterior (no acumula)', async () => {
    api.get.mockResolvedValueOnce({ data: RESPUESTA })
    await ejecutarBootstrap()

    api.get.mockResolvedValueOnce({ data: { ...RESPUESTA, ecas: [] } })
    await ejecutarBootstrap()

    const ecas = await leerEcasLocal()
    expect(ecas).toEqual([])
  })
})

describe('ejecutarPull', () => {
  it('manda `desde` con el generado_en del último bootstrap', async () => {
    api.get.mockResolvedValueOnce({ data: RESPUESTA })
    await ejecutarBootstrap()

    api.get.mockResolvedValueOnce({ data: RESPUESTA })
    await ejecutarPull()

    expect(api.get).toHaveBeenLastCalledWith('/sync/pull', { params: { desde: RESPUESTA.generado_en } })
  })

  it('sin bootstrap previo, no manda `desde`', async () => {
    api.get.mockResolvedValueOnce({ data: RESPUESTA })

    await ejecutarPull()

    expect(api.get).toHaveBeenLastCalledWith('/sync/pull', { params: {} })
  })
})
