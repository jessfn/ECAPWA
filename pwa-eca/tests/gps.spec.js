// pwa-eca — pruebas del servicio de GPS (ECA-014 + rediseño de velocidad).
// El flujo nuevo prioriza rapidez: resuelve APENAS logra una lectura bajo
// el umbral, acepta caché reciente vía `getCurrentPosition`, y si a
// `objetivoMs` no hay una "buena" entrega la mejor imprecisa. Tope duro
// corto como salvavidas.
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

// `getCurrentPosition` por defecto no llama a ningún callback (el watch
// dirige la prueba); cada test puede sobreescribirlo. `clearWatch` se
// registra para afirmar la limpieza.
function mockGeolocation({ watchPosition, getCurrentPosition = vi.fn(), clearWatch = vi.fn() } = {}) {
  global.navigator.geolocation = { watchPosition, getCurrentPosition, clearWatch }
}

describe('capturarGps (flujo rápido)', () => {
  it('SIN_GPS si el navegador no tiene geolocation', async () => {
    delete global.navigator.geolocation
    const resultado = await capturarGps()
    expect(resultado).toEqual({ estado_gps: 'SIN_GPS' })
  })

  it('CON_GPS al instante cuando la primera lectura ya está bajo el umbral (no espera)', async () => {
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

    const promesa = capturarGps()
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 8 } })
    // Sin avanzar temporizadores: debe resolver de inmediato.
    const resultado = await promesa

    expect(resultado.estado_gps).toBe('CON_GPS')
    expect(resultado.latitud).toBe(19.4)
    expect(resultado.precision_gps_m).toBe(8)
    expect(clearWatch).toHaveBeenCalledWith(1)
  })

  it('ruta veloz: un fix en caché de getCurrentPosition resuelve al instante', async () => {
    mockGeolocation({
      watchPosition: () => 1,
      getCurrentPosition: (ok) => ok({ coords: { latitude: 20, longitude: -100, accuracy: 15 } }),
    })

    const resultado = await capturarGps()

    expect(resultado.estado_gps).toBe('CON_GPS')
    expect(resultado.latitud).toBe(20)
  })

  it('GPS_IMPRECISO: a objetivoMs entrega la mejor lectura aunque exceda el umbral', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    let onExito
    mockGeolocation({
      watchPosition: (ok) => {
        onExito = ok
        return 1
      },
    })

    const promesa = capturarGps({ objetivoMs: 1000 })
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 120 } })
    await vi.advanceTimersByTimeAsync(1000)

    expect((await promesa).estado_gps).toBe('GPS_IMPRECISO')
  })

  it('se queda con la lectura de mejor precisión entre varias antes del objetivo', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    let onExito
    mockGeolocation({
      watchPosition: (ok) => {
        onExito = ok
        return 1
      },
    })

    const promesa = capturarGps({ objetivoMs: 1000 })
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 200 } })
    await vi.advanceTimersByTimeAsync(200)
    // Llega una lectura bajo el umbral → resuelve ya con esa (CON_GPS).
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 10 } })

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

    const promesa = capturarGps({ objetivoMs: 1000 })
    // Dos lecturas imprecisas (ninguna bajo umbral); se queda con la mejor.
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 90 } })
    await vi.advanceTimersByTimeAsync(200)
    onExito({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 200 } })
    await vi.advanceTimersByTimeAsync(1000)

    expect((await promesa).precision_gps_m).toBe(90)
  })

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

    const promesa = capturarGps({ timeoutMs: 10000 })
    await vi.advanceTimersByTimeAsync(10000)

    expect((await promesa).estado_gps).toBe('SIN_GPS')
  })

  it('no se cuelga si el navegador nunca llama a ningún callback (permiso pendiente)', async () => {
    mockGeolocation({
      watchPosition: () => 1,
    })

    const promesa = capturarGps({ timeoutMs: 10000 })
    await vi.advanceTimersByTimeAsync(12000)
    const resultado = await promesa

    expect(resultado.estado_gps).toBe('SIN_GPS')
  })
})
