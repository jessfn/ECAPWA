// pwa-eca — pruebas del modal de confirmación de Jornada.
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import JornadaAccionModal from '../src/components/JornadaAccionModal.vue'

vi.mock('../src/services/gps', () => ({
  capturarGps: vi.fn(async () => ({ estado_gps: 'SIN_GPS' })),
}))

import { capturarGps } from '../src/services/gps'

describe('JornadaAccionModal', () => {
  // Regresión real: el estado inicial de `fase` ya es BUSCANDO (para que
  // el radar arranque animado desde el primer render). Un guard mal puesto
  // en `buscarUbicacion` tipo `if (fase.value === FASE.BUSCANDO) return`
  // cortaba la captura automática de `onMounted` ANTES de llamar a
  // `capturarGps` — el modal se quedaba para siempre en "Obteniendo tu
  // ubicación…", sin fallar ni mostrar ningún error.
  it('llama a capturarGps al montarse y sale de la fase "buscando"', async () => {
    const wrapper = mount(JornadaAccionModal, {
      props: { tipo: 'inicio' },
      global: { stubs: { Teleport: true } },
    })

    // Deja correr los microtasks pendientes (await dentro de onMounted).
    await vi.waitFor(() => {
      expect(capturarGps).toHaveBeenCalled()
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).not.toContain('Obteniendo…')
    expect(wrapper.text()).toContain('Sin ubicación')

    wrapper.unmount()
  })
})
