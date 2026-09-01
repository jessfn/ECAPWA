// admin-eca — pruebas del interceptor de refresh en 401 (ECA-005).
import { describe, it, expect, beforeEach, vi } from 'vitest'

const instanciaAxios = vi.fn(() => Promise.resolve({ data: 'reintento-ok' }))
instanciaAxios.interceptors = {
  request: { use: vi.fn() },
  response: { use: vi.fn() },
}

vi.mock('axios', () => ({
  default: { create: vi.fn(() => instanciaAxios) },
}))

const authFalso = {
  refrescar: vi.fn(),
  cerrarSesionLocal: vi.fn(),
  accessToken: null,
}
vi.mock('../src/stores/auth', () => ({
  useAuthStore: () => authFalso,
}))

const { api, manejarErrorDeRespuesta, _reiniciarStoreAuthParaPruebas } = await import(
  '../src/services/api'
)

function crearError401(url, extra = {}) {
  return {
    response: { status: 401 },
    config: { url, headers: {}, ...extra },
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  _reiniciarStoreAuthParaPruebas()
  authFalso.accessToken = null
  instanciaAxios.mockClear()
})

describe('manejarErrorDeRespuesta', () => {
  it('en un 401 normal, refresca y reintenta la petición original con el token nuevo', async () => {
    authFalso.refrescar.mockResolvedValueOnce('token-nuevo')
    authFalso.accessToken = 'token-nuevo'
    const error = crearError401('/usuarios')

    await manejarErrorDeRespuesta(error)

    expect(authFalso.refrescar).toHaveBeenCalledTimes(1)
    expect(instanciaAxios).toHaveBeenCalledTimes(1)
    const [peticionReintentada] = instanciaAxios.mock.calls[0]
    expect(peticionReintentada.headers.Authorization).toBe('Bearer token-nuevo')
    expect(peticionReintentada._reintentada).toBe(true)
  })

  it('si el refresh también falla, cierra sesión local y propaga el error', async () => {
    const errorDeRefresh = new Error('refresh token inválido')
    authFalso.refrescar.mockRejectedValueOnce(errorDeRefresh)
    const error = crearError401('/usuarios')

    await expect(manejarErrorDeRespuesta(error)).rejects.toBe(errorDeRefresh)
    expect(authFalso.cerrarSesionLocal).toHaveBeenCalledTimes(1)
    expect(instanciaAxios).not.toHaveBeenCalled()
  })

  it('un 401 en /auth/login no dispara refresh (evita bucle)', async () => {
    const error = crearError401('/auth/login')

    await expect(manejarErrorDeRespuesta(error)).rejects.toBe(error)
    expect(authFalso.refrescar).not.toHaveBeenCalled()
  })

  it('un 401 en /auth/refresh no dispara otro refresh (evita bucle)', async () => {
    const error = crearError401('/auth/refresh')

    await expect(manejarErrorDeRespuesta(error)).rejects.toBe(error)
    expect(authFalso.refrescar).not.toHaveBeenCalled()
  })

  it('una petición ya reintentada no vuelve a intentar refresh', async () => {
    const error = crearError401('/usuarios', { _reintentada: true })

    await expect(manejarErrorDeRespuesta(error)).rejects.toBe(error)
    expect(authFalso.refrescar).not.toHaveBeenCalled()
  })

  it('un error que no es 401 se propaga sin tocar la sesión', async () => {
    const error = { response: { status: 500 }, config: { url: '/usuarios', headers: {} } }

    await expect(manejarErrorDeRespuesta(error)).rejects.toBe(error)
    expect(authFalso.refrescar).not.toHaveBeenCalled()
  })
})
