// pwa-eca — pruebas del servicio de GPS (ECA-014 + ECA-021: watchPosition,
// mismo flujo que pwasuper).
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

vi.mock('../src/services/parametrosConfigService', () => ({
  obtenerParametro: vi.fn(async (_clave, { porDefecto }) => porDefecto),
}))

import { obtenerParametro } from '../src/services/parametrosConfigService'
import { capturarGps } from '../src/services/gps'

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

// `mockWatchPosition(fn)` deja que cada test controle cuándo/qué emite el
// watch; `clearWatch` se registra para poder afirmar que se limpia bien.
function mockGeolocation({ watchPosition, clearWatch = vi.fn() } = {}) {
  global.navigator.geolocation = { watchPosition, clearWatch }
}

describe('capturarGps', () => {
  it('SIN_GPS si el navegador no tiene geolocation', async () => {
    delete global.navigator.geolocation
    const resultado = await capturarGps()
    expect(resultado).toEqual({ estado_gps: 'SIN_GPS' })
  })

  it('CON_GPS cuando la precisión está dentro del umbral', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    let onExito
    const clearWatch = vi.fn()
    mockGeolocation({
      watchPosition: (ok) => {
        onExito = ok
        return 1
      },
      clearWatch,
    })

    const promesa = capturarGps({ maxEsperaMejorPrecisionMs: 3000 })
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 8 } })
    await vi.advanceTimersByTimeAsync(3000)
    const resultado = await promesa

    expect(resultado.estado_gps).toBe('CON_GPS')
    expect(resultado.latitud).toBe(19.4)
    expect(resultado.precision_gps_m).toBe(8)
    expect(clearWatch).toHaveBeenCalledWith(1)
  })

  it('GPS_IMPRECISO cuando la precisión excede el umbral', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    let onExito
    mockGeolocation({
      watchPosition: (ok) => {
        onExito = ok
        return 1
      },
    })

    const promesa = capturarGps({ maxEsperaMejorPrecisionMs: 1000 })
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 120 } })
    await vi.advanceTimersByTimeAsync(1000)

    expect((await promesa).estado_gps).toBe('GPS_IMPRECISO')
  })

  it('se queda con la lectura de mejor precisión entre varias', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    let onExito
    mockGeolocation({
      watchPosition: (ok) => {
        onExito = ok
        return 1
      },
    })

    const promesa = capturarGps({ maxEsperaMejorPrecisionMs: 1000 })
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 200 } })
    await vi.advanceTimersByTimeAsync(200)
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 10 } })
    await vi.advanceTimersByTimeAsync(1000)

    const resultado = await promesa
    expect(resultado.precision_gps_m).toBe(10)
    expect(resultado.estado_gps).toBe('CON_GPS')
  })

  it('una lectura peor que la ya obtenida no la reemplaza', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    let onExito
    mockGeolocation({
      watchPosition: (ok) => {
        onExito = ok
        return 1
      },
    })

    const promesa = capturarGps({ maxEsperaMejorPrecisionMs: 1000 })
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 10 } })
    await vi.advanceTimersByTimeAsync(200)
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 200 } })
    await vi.advanceTimersByTimeAsync(1000)

    expect((await promesa).precision_gps_m).toBe(10)
  })

  // El código 1 es `PERMISSION_DENIED` en la spec real — a diferencia de
  // un error genérico, esto sí debe marcarse para que la UI pida activar
  // el permiso en vez de solo decir "sin señal", y resuelve de inmediato
  // (no tiene caso seguir esperando).
  it('marca permiso_denegado cuando el navegador niega el permiso', async () => {
    let onError
    mockGeolocation({
      watchPosition: (_ok, err) => {
        onError = err
        return 1
      },
    })

    const promesa = capturarGps()
    onError({ code: 1, message: 'User denied Geolocation' })
    const resultado = await promesa

    expect(resultado.estado_gps).toBe('SIN_GPS')
    expect(resultado.permiso_denegado).toBe(true)
  })

  it('SIN_GPS si nunca llega ninguna lectura antes del tope', async () => {
    mockGeolocation({ watchPosition: () => 1 })

    const promesa = capturarGps({ timeoutMs: 15000 })
    await vi.advanceTimersByTimeAsync(15000)

    expect((await promesa).estado_gps).toBe('SIN_GPS')
  })

  // Regresión real observada: mientras el navegador tiene pendiente el
  // diálogo nativo de permiso de ubicación, ni `watchPosition` ni su error
  // llegan a llamarse — sin un salvavidas por `setTimeout` (que sí corre
  // siempre, sin depender de que el navegador resuelva el diálogo), la
  // captura se queda colgada sin límite.
  it('no se cuelga si el navegador nunca llama a ningún callback (permiso pendiente)', async () => {
    mockGeolocation({
      watchPosition: () => {
        /* nunca llama a onExito ni a onError */
        return 1
      },
    })

    const promesa = capturarGps({ timeoutMs: 15000 })
    await vi.advanceTimersByTimeAsync(20000)
    const resultado = await promesa

    expect(resultado.estado_gps).toBe('SIN_GPS')
  })
})
