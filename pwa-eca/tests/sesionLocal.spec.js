// pwa-eca — pruebas de la sesión local offline (ECA-011, §2.2).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  guardarSesionLocal,
  leerSesionLocal,
  limpiarSesionLocal,
  sesionLocalVigente,
} from '../src/services/sesionLocal'

beforeEach(() => {
  localStorage.clear()
  vi.unstubAllEnvs()
})

describe('sesionLocal', () => {
  it('una marca recién guardada está vigente', () => {
    guardarSesionLocal({ usuario: { nombre: 'Ana' }, permisos: ['actividades.crear'] })
    expect(sesionLocalVigente()).toBe(true)
  })

  it('sin marca guardada, no está vigente', () => {
    expect(sesionLocalVigente()).toBe(false)
  })

  it('una marca más vieja que la validez configurada deja de estar vigente, pero NO se borra', () => {
    vi.stubEnv('VITE_OFFLINE_SESSION_DIAS', '1')
    const hace2Dias = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
    localStorage.setItem(
      'eca_tecnico_sesion_local',
      JSON.stringify({ usuario: { nombre: 'Ana' }, permisos: [], validada_en: hace2Dias }),
    )

    expect(sesionLocalVigente()).toBe(false)
    // La marca sigue ahí: un pendiente en outbox no se pierde por esto.
    expect(leerSesionLocal()).not.toBeNull()
  })

  it('limpiarSesionLocal borra la marca explícitamente', () => {
    guardarSesionLocal({ usuario: { nombre: 'Ana' }, permisos: [] })
    limpiarSesionLocal()
    expect(leerSesionLocal()).toBeNull()
    expect(sesionLocalVigente()).toBe(false)
  })
})
