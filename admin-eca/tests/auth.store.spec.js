// admin-eca — pruebas del store `auth` (ECA-005).
// Criterios pedidos por el ticket: guarda token, detecta expiración, limpia en logout.
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../src/services/api', () => ({
  api: { post: vi.fn(), get: vi.fn() },
}))

import { api } from '../src/services/api'
import { useAuthStore } from '../src/stores/auth'

// JWT de prueba sin firma real (el store solo lee `exp`, nunca verifica firma en cliente).
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
  it('guarda el access/refresh token y el perfil tras login', async () => {
    api.post.mockResolvedValueOnce({
      data: { access_token: TOKEN_VIGENTE, refresh_token: 'refresco-1', expira_en: '2099-01-01T00:00:00Z' },
    })
    api.get.mockResolvedValueOnce({
      data: { usuario: { nombre: 'Ana' }, permisos: ['usuarios.gestionar'] },
    })

    const auth = useAuthStore()
    await auth.login('ana@ejemplo.org', 'Correcta123')

    expect(auth.accessToken).toBe(TOKEN_VIGENTE)
    expect(auth.refreshToken).toBe('refresco-1')
    expect(auth.usuario).toEqual({ nombre: 'Ana' })
    expect(auth.permisos).toEqual(['usuarios.gestionar'])
    expect(localStorage.getItem('eca_admin_access_token')).toBe(TOKEN_VIGENTE)
    expect(auth.estaAutenticado).toBe(true)
  })

  it('detecta un access token expirado como no autenticado', () => {
    localStorage.setItem('eca_admin_access_token', TOKEN_EXPIRADO)
    const auth = useAuthStore()

    expect(auth.estaAutenticado).toBe(false)
  })

  it('sin token en absoluto, no está autenticado', () => {
    const auth = useAuthStore()
    expect(auth.estaAutenticado).toBe(false)
  })

  it('tienePermiso refleja los permisos cargados', async () => {
    api.post.mockResolvedValueOnce({
      data: { access_token: TOKEN_VIGENTE, refresh_token: 'r1', expira_en: '2099-01-01T00:00:00Z' },
    })
    api.get.mockResolvedValueOnce({ data: { usuario: { nombre: 'Ana' }, permisos: ['ecas.ver'] } })

    const auth = useAuthStore()
    await auth.login('ana@ejemplo.org', 'Correcta123')

    expect(auth.tienePermiso('ecas.ver')).toBe(true)
    expect(auth.tienePermiso('usuarios.gestionar')).toBe(false)
  })

  it('logout limpia el estado y el localStorage aunque el backend falle', async () => {
    localStorage.setItem('eca_admin_access_token', TOKEN_VIGENTE)
    localStorage.setItem('eca_admin_refresh_token', 'r1')
    localStorage.setItem('eca_admin_usuario', JSON.stringify({ nombre: 'Ana' }))
    localStorage.setItem('eca_admin_permisos', JSON.stringify(['ecas.ver']))
    api.post.mockRejectedValueOnce(new Error('red caída'))

    const auth = useAuthStore()
    await auth.logout()

    expect(auth.accessToken).toBeNull()
    expect(auth.refreshToken).toBeNull()
    expect(auth.usuario).toBeNull()
    expect(auth.permisos).toEqual([])
    expect(localStorage.getItem('eca_admin_access_token')).toBeNull()
    expect(localStorage.getItem('eca_admin_refresh_token')).toBeNull()
  })

  it('refrescar sin refresh token lanza en vez de llamar al backend', async () => {
    const auth = useAuthStore()
    await expect(auth.refrescar()).rejects.toThrow()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('refrescar rota el par de tokens', async () => {
    localStorage.setItem('eca_admin_refresh_token', 'r1')
    api.post.mockResolvedValueOnce({
      data: { access_token: TOKEN_VIGENTE, refresh_token: 'r2', expira_en: '2099-01-01T00:00:00Z' },
    })

    const auth = useAuthStore()
    auth.refreshToken = 'r1'
    await auth.refrescar()

    expect(auth.refreshToken).toBe('r2')
    expect(localStorage.getItem('eca_admin_refresh_token')).toBe('r2')
  })
})
