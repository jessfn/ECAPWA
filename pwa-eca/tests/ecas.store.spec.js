// pwa-eca — pruebas del store `ecas` offline (ECA-018).
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../src/services/bootstrap', () => ({
  leerEcasLocal: vi.fn(),
  ejecutarBootstrap: vi.fn(),
}))

import { leerEcasLocal, ejecutarBootstrap } from '../src/services/bootstrap'
import { useEcasStore } from '../src/stores/ecas'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('useEcasStore', () => {
  it('cargar lee de IndexedDB sin llamar a bootstrap si ya hay datos', async () => {
    leerEcasLocal.mockResolvedValueOnce([{ eca_id: 1, eca_nombre: 'ECA 1' }])

    const ecas = useEcasStore()
    await ecas.cargar()

    expect(ecas.items).toHaveLength(1)
    expect(ejecutarBootstrap).not.toHaveBeenCalled()
  })

  it('buscar filtra localmente por nombre, sin distinguir mayúsculas', async () => {
    leerEcasLocal.mockResolvedValueOnce([
      { eca_id: 1, eca_nombre: 'Escuela Norte' },
      { eca_id: 2, eca_nombre: 'Escuela Sur' },
    ])
    const ecas = useEcasStore()
    await ecas.cargar()

    expect(ecas.buscar('norte')).toEqual([{ eca_id: 1, eca_nombre: 'Escuela Norte' }])
  })

  it('buscar sin texto devuelve todas', async () => {
    leerEcasLocal.mockResolvedValueOnce([{ eca_id: 1, eca_nombre: 'A' }])
    const ecas = useEcasStore()
    await ecas.cargar()

    expect(ecas.buscar('')).toEqual(ecas.items)
  })
})
