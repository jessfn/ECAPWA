// pwa-eca — pruebas del store `auth` (ECA-011).
// Cubre el criterio central del ticket: el guard permite con sesión de
// servidor O con sesión local vigente, y bloquea sin ninguna de las dos.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../src/services/api', () => ({
  api: { post: vi.fn(), get: vi.fn() },
}))

import { api } from '../src/services/api'
import { useAuthStore } from '../src/stores/auth'
import { guardarSesionLocal } from '../src/services/sesionLocal'

function crearJwt(payload) {
  const base64Url = (obj) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${base64Url({ alg: 'HS256' })}.${base64Url(payload)}.firma-falsa`
}

const AHORA_SEGUNDOS = Math.floor(Date.now() / 1000)
const TOKEN_VIGENTE = crearJwt({ sub: '1', exp: AHORA_SEGUNDOS + 900 })
const TOKEN_EXPIRADO = crearJwt({ sub: '1', exp: AHORA_SEGUNDOS - 900 })

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('useAuthStore', () => {
  it('login guarda tokens y crea la marca de sesión local (bootstrap)', async () => {
    api.post.mockResolvedValueOnce({
      data: { access_token: TOKEN_VIGENTE, refresh_token: 'r1', expira_en: '2099-01-01T00:00:00Z' },
    })
    api.get.mockResolvedValueOnce({
      data: { usuario: { nombre: 'Ana' }, permisos: ['actividades.crear'] },
    })

    const auth = useAuthStore()
    await auth.login('ana@ejemplo.org', 'Correcta123')

    expect(auth.accessToken).toBe(TOKEN_VIGENTE)
    expect(auth.estaAutenticado).toBe(true)
    expect(auth.sesionLocalVigente).toBe(true)
    expect(localStorage.getItem('eca_tecnico_sesion_local')).not.toBeNull()
  })

  it('con access token expirado pero sesión local vigente, sigue autenticado', () => {
    localStorage.setItem('eca_tecnico_access_token', TOKEN_EXPIRADO)
    guardarSesionLocal({ usuario: { nombre: 'Ana' }, permisos: ['actividades.crear'] })

    const auth = useAuthStore()

    expect(auth.sesionServidorValida).toBe(false)
    expect(auth.sesionLocalVigente).toBe(true)
    expect(auth.estaAutenticado).toBe(true)
  })

  it('sin token y sin sesión local, no está autenticado', () => {
    const auth = useAuthStore()
    expect(auth.estaAutenticado).toBe(false)
  })

  it('con sesión local vencida y sin token de servidor, no está autenticado', () => {
    vi.stubEnv('VITE_OFFLINE_SESSION_DIAS', '1')
    const hace2Dias = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
    localStorage.setItem(
      'eca_tecnico_sesion_local',
      JSON.stringify({ usuario: { nombre: 'Ana' }, permisos: [], validada_en: hace2Dias }),
    )

    const auth = useAuthStore()
    expect(auth.estaAutenticado).toBe(false)
    vi.unstubAllEnvs()
  })

  it('logout limpia tokens y la sesión local', async () => {
    localStorage.setItem('eca_tecnico_access_token', TOKEN_VIGENTE)
    localStorage.setItem('eca_tecnico_refresh_token', 'r1')
    guardarSesionLocal({ usuario: { nombre: 'Ana' }, permisos: [] })
    api.post.mockRejectedValueOnce(new Error('red caída'))

    const auth = useAuthStore()
    await auth.logout()

    expect(auth.accessToken).toBeNull()
    expect(auth.refreshToken).toBeNull()
    expect(auth.usuario).toBeNull()
    expect(localStorage.getItem('eca_tecnico_access_token')).toBeNull()
    expect(localStorage.getItem('eca_tecnico_sesion_local')).toBeNull()
  })

  it('cerrarSesionDeServidor NO borra la sesión local', () => {
    localStorage.setItem('eca_tecnico_access_token', TOKEN_VIGENTE)
    guardarSesionLocal({ usuario: { nombre: 'Ana' }, permisos: ['actividades.crear'] })

    const auth = useAuthStore()
    auth.cerrarSesionDeServidor()

    expect(auth.accessToken).toBeNull()
    expect(localStorage.getItem('eca_tecnico_sesion_local')).not.toBeNull()
    expect(auth.estaAutenticado).toBe(true) // sigue autenticado vía sesión local
  })

  it('refrescar sin refresh token lanza en vez de llamar al backend', async () => {
    const auth = useAuthStore()
    await expect(auth.refrescar()).rejects.toThrow()
    expect(api.post).not.toHaveBeenCalled()
  })
})
