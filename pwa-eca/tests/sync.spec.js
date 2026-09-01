// pwa-eca — pruebas del motor de sincronización (ECA-017).
import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('../src/services/outbox', () => ({
  listar: vi.fn(),
  marcarEstado: vi.fn(),
}))
vi.mock('../src/services/syncPushService', () => ({
  registrarDispositivo: vi.fn(),
  push: vi.fn(),
}))
vi.mock('../src/services/evidenciasService', () => ({
  subirEvidencia: vi.fn(),
}))

import { listar, marcarEstado } from '../src/services/outbox'
import { registrarDispositivo, push } from '../src/services/syncPushService'
import { subirEvidencia } from '../src/services/evidenciasService'
import { sincronizar, _reiniciarSyncParaPruebas } from '../src/services/sync'

function authFalso({ sesionServidorValida = true, refrescarFalla = false } = {}) {
  return {
    sesionServidorValida,
    refrescar: refrescarFalla ? vi.fn().mockRejectedValue(new Error('sin refresh')) : vi.fn().mockResolvedValue(),
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  _reiniciarSyncParaPruebas()
  localStorage.clear()
  Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })
  registrarDispositivo.mockResolvedValue({})
  listar.mockImplementation(async (tienda) => {
    if (tienda === 'outbox_jornadas') return []
    if (tienda === 'outbox_actividades') return []
    if (tienda === 'outbox_evidencias') return []
    return []
  })
})

describe('sincronizar', () => {
  it('sin red, no toca el outbox y avisa sin_red', async () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true })

    const resultado = await sincronizar(authFalso())

    expect(resultado).toEqual({ ok: false, motivo: 'sin_red', aplicados: 0, duplicados: 0, rechazados: 0 })
    expect(push).not.toHaveBeenCalled()
    expect(marcarEstado).not.toHaveBeenCalled()
  })

  it('si no se puede recuperar la sesión, deja el outbox intacto', async () => {
    const auth = authFalso({ sesionServidorValida: false, refrescarFalla: true })
    listar.mockImplementation(async (tienda) => (tienda === 'outbox_actividades' ? [{ uuid: 'a1', estado_local: 'PENDIENTE' }] : []))

    const resultado = await sincronizar(auth)

    expect(resultado.motivo).toBe('sin_sesion')
    expect(push).not.toHaveBeenCalled()
    expect(marcarEstado).not.toHaveBeenCalled()
  })

  it('sin nada pendiente, no llama a push', async () => {
    const resultado = await sincronizar(authFalso())

    expect(resultado).toEqual({ ok: true, motivo: 'nada_pendiente', aplicados: 0, duplicados: 0, rechazados: 0 })
    expect(push).not.toHaveBeenCalled()
  })

  it('envía lo pendiente y marca SINCRONIZADO lo aplicado/duplicado, RECHAZADO lo rechazado', async () => {
    listar.mockImplementation(async (tienda) => {
      if (tienda === 'outbox_jornadas') return [{ uuid: 'j1', estado_local: 'PENDIENTE', inicio_en: '2026-01-01T08:00:00Z' }]
      if (tienda === 'outbox_actividades') {
        return [
          { uuid: 'a1', estado_local: 'PENDIENTE', jornada_uuid: 'j1', modalidad_id: 1, tipo_actividad_id: 1, descripcion: 'x', fecha_hora: '2026-01-01T09:00:00Z' },
          { uuid: 'a2', estado_local: 'RECHAZADO', jornada_uuid: 'j1', modalidad_id: 1, tipo_actividad_id: 1, descripcion: 'y', fecha_hora: '2026-01-01T09:00:00Z' },
        ]
      }
      if (tienda === 'outbox_evidencias') return []
      return []
    })
    push.mockResolvedValueOnce({
      resultados: [
        { uuid: 'j1', resultado: 'APLICADO' },
        { uuid: 'a1', resultado: 'APLICADO' },
        { uuid: 'a2', resultado: 'RECHAZADO', error: 'ECA requerida' },
      ],
    })

    const resultado = await sincronizar(authFalso())

    expect(resultado).toEqual({ ok: true, aplicados: 2, duplicados: 0, rechazados: 1 })
    expect(marcarEstado).toHaveBeenCalledWith('outbox_jornadas', 'j1', 'SINCRONIZANDO')
    expect(marcarEstado).toHaveBeenCalledWith('outbox_jornadas', 'j1', 'SINCRONIZADO')
    expect(marcarEstado).toHaveBeenCalledWith('outbox_actividades', 'a1', 'SINCRONIZADO')
    expect(marcarEstado).toHaveBeenCalledWith('outbox_actividades', 'a2', 'RECHAZADO', { ultimoError: 'ECA requerida' })
  })

  it('un error de red en push deja todo de vuelta en PENDIENTE (no se pierde nada)', async () => {
    listar.mockImplementation(async (tienda) =>
      tienda === 'outbox_actividades'
        ? [{ uuid: 'a1', estado_local: 'PENDIENTE', jornada_uuid: 'j1', modalidad_id: 1, tipo_actividad_id: 1, descripcion: 'x', fecha_hora: '2026-01-01T09:00:00Z' }]
        : [],
    )
    push.mockRejectedValue(new Error('network error')) // sin `.response` → error de red

    const resultado = await sincronizar(authFalso())

    expect(resultado.motivo).toBe('error_red')
    expect(marcarEstado).toHaveBeenCalledWith('outbox_actividades', 'a1', 'SINCRONIZANDO')
    expect(marcarEstado).toHaveBeenCalledWith('outbox_actividades', 'a1', 'PENDIENTE')
  })

  it('sube evidencias solo de actividades confirmadas (APLICADO/DUPLICADO), no de las RECHAZADO', async () => {
    listar.mockImplementation(async (tienda) => {
      if (tienda === 'outbox_actividades') {
        return [
          { uuid: 'a1', estado_local: 'PENDIENTE', jornada_uuid: 'j1', modalidad_id: 1, tipo_actividad_id: 1, descripcion: 'x', fecha_hora: '2026-01-01T09:00:00Z' },
          { uuid: 'a2', estado_local: 'PENDIENTE', jornada_uuid: 'j1', modalidad_id: 1, tipo_actividad_id: 1, descripcion: 'y', fecha_hora: '2026-01-01T09:00:00Z' },
        ]
      }
      if (tienda === 'outbox_evidencias') {
        return [
          { uuid: 'e1', actividad_uuid: 'a1', estado_local: 'PENDIENTE', orden: 1, archivo: new Blob() },
          { uuid: 'e2', actividad_uuid: 'a2', estado_local: 'PENDIENTE', orden: 1, archivo: new Blob() },
        ]
      }
      return []
    })
    push.mockResolvedValueOnce({
      resultados: [
        { uuid: 'a1', resultado: 'APLICADO' },
        { uuid: 'a2', resultado: 'RECHAZADO', error: 'motivo' },
      ],
    })
    subirEvidencia.mockResolvedValue({ uuid: 'e1' })

    await sincronizar(authFalso())

    expect(subirEvidencia).toHaveBeenCalledTimes(1)
    expect(subirEvidencia).toHaveBeenCalledWith('a1', expect.objectContaining({ uuid: 'e1' }))
    expect(marcarEstado).toHaveBeenCalledWith('outbox_evidencias', 'e1', 'SINCRONIZADO')
  })
})
