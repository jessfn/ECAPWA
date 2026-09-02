// pwa-eca — pruebas del servicio de GPS (ECA-014).
import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('../src/services/parametrosConfigService', () => ({
  obtenerParametro: vi.fn(async (_clave, { porDefecto }) => porDefecto),
}))

import { obtenerParametro } from '../src/services/parametrosConfigService'
import { capturarGps } from '../src/services/gps'

beforeEach(() => {
  vi.clearAllMocks()
})

function mockGeolocation(fn) {
  global.navigator.geolocation = { getCurrentPosition: fn }
}

describe('capturarGps', () => {
  it('SIN_GPS si el navegador no tiene geolocation', async () => {
    delete global.navigator.geolocation
    const resultado = await capturarGps()
    expect(resultado).toEqual({ estado_gps: 'SIN_GPS' })
  })

  it('SIN_GPS si el usuario niega el permiso', async () => {
    mockGeolocation((_ok, err) => err(new Error('denegado')))
    const resultado = await capturarGps({ intentos: 2 })
    expect(resultado.estado_gps).toBe('SIN_GPS')
  })

  // El código 1 es `PERMISSION_DENIED` en la spec real de
  // `GeolocationPositionError` — a diferencia de un Error genérico (test de
  // arriba), esto sí debe marcarse para que la UI pida activar el permiso
  // en vez de solo decir "sin señal", y no vale la pena seguir reintentando.
  it('marca permiso_denegado y no reintenta cuando el navegador niega el permiso', async () => {
    let llamadas = 0
    mockGeolocation((_ok, err) => {
      llamadas += 1
      err({ code: 1, message: 'User denied Geolocation' })
    })

    const resultado = await capturarGps({ intentos: 4 })

    expect(resultado.estado_gps).toBe('SIN_GPS')
    expect(resultado.permiso_denegado).toBe(true)
    expect(llamadas).toBe(1)
  })

  it('SIN_GPS si hay timeout en todos los intentos', async () => {
    mockGeolocation((_ok, err) => err(new Error('timeout')))
    const resultado = await capturarGps({ intentos: 3 })
    expect(resultado.estado_gps).toBe('SIN_GPS')
  })

  it('CON_GPS cuando la precisión está dentro del umbral', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    mockGeolocation((ok) => ok({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 8 } }))

    const resultado = await capturarGps({ intentos: 1 })

    expect(resultado.estado_gps).toBe('CON_GPS')
    expect(resultado.latitud).toBe(19.4)
    expect(resultado.precision_gps_m).toBe(8)
  })

  it('GPS_IMPRECISO cuando la precisión excede el umbral', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    mockGeolocation((ok) => ok({ coords: { latitude: 19.4, longitude: -99.1, accuracy: 120 } }))

    const resultado = await capturarGps({ intentos: 1 })

    expect(resultado.estado_gps).toBe('GPS_IMPRECISO')
  })

  it('se queda con el mejor de varios intentos', async () => {
    obtenerParametro.mockResolvedValueOnce(30)
    let llamada = 0
    mockGeolocation((ok) => {
      llamada += 1
      const accuracy = llamada === 1 ? 200 : 10
      ok({ coords: { latitude: 19.4, longitude: -99.1, accuracy } })
    })

    const resultado = await capturarGps({ intentos: 2 })

    expect(resultado.precision_gps_m).toBe(10)
    expect(resultado.estado_gps).toBe('CON_GPS')
  })
})
