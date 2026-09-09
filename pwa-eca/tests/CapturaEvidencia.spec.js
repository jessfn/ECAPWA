// pwa-eca — pruebas de captura de evidencias (ECA-015).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import CapturaEvidencia from '../src/components/CapturaEvidencia.vue'

vi.mock('../src/services/imagen', () => ({
  comprimirImagen: vi.fn(),
  blobAArchivo: vi.fn((blob, nombre) => new File([blob], nombre, { type: 'image/jpeg' })),
}))

import { comprimirImagen } from '../src/services/imagen'

function archivoDe(nombre, tipo = 'image/jpeg') {
  return new File(['contenido'], nombre, { type: tipo })
}

function dispararSeleccion(wrapper, archivos) {
  const input = wrapper.find('.captura-evidencia__boton--galeria input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: archivos, configurable: true })
  return input.trigger('change')
}

beforeEach(() => {
  vi.clearAllMocks()
  URL.createObjectURL = vi.fn(() => 'blob:fake')
  URL.revokeObjectURL = vi.fn()
})

describe('CapturaEvidencia', () => {
  // Pedido explícito (2026-09-07): "se deben subir las imágenes como sea,
  // sin importar el tamaño" — una foto nunca debe perderse por no
  // poderse comprimir. Bug real: antes el `try/catch` envolvía el `for`
  // completo, así que UNA foto que fallara al comprimirse (celular con
  // poca memoria, formato no decodificable, etc.) abortaba el resto del
  // lote Y esa foto se perdía sin subir ni comprimida ni original.
  it('si la compresión falla, sube el archivo ORIGINAL en vez de perder la foto', async () => {
    comprimirImagen.mockRejectedValueOnce(new Error('no se pudo decodificar'))
    const wrapper = mount(CapturaEvidencia, { props: { minFotos: 1, maxFotos: 3 } })

    const original = archivoDe('foto-pesada.jpg')
    await dispararSeleccion(wrapper, [original])
    await wrapper.vm.$nextTick()

    const emitido = wrapper.emitted('update:fotos')
    expect(emitido).toBeTruthy()
    const fotos = emitido[emitido.length - 1][0]
    expect(fotos).toHaveLength(1)
    expect(fotos[0].archivo).toBe(original) // el original, no un archivo perdido
    expect(wrapper.text()).not.toContain('No se pudo procesar')
  })

  it('si falla la primera foto de dos, la segunda se procesa igual (no aborta el lote)', async () => {
    comprimirImagen.mockRejectedValueOnce(new Error('falla')).mockResolvedValueOnce(new Blob(['ok']))
    const wrapper = mount(CapturaEvidencia, { props: { minFotos: 1, maxFotos: 3 } })

    const original1 = archivoDe('a.jpg')
    const original2 = archivoDe('b.jpg')
    await dispararSeleccion(wrapper, [original1, original2])
    await wrapper.vm.$nextTick()

    const emitido = wrapper.emitted('update:fotos')
    const fotos = emitido[emitido.length - 1][0]
    expect(fotos).toHaveLength(2)
    expect(fotos[0].archivo).toBe(original1)
    expect(fotos[1].archivo).not.toBe(original2) // esta sí se comprimió
  })

  it('comprime normalmente cuando no hay error', async () => {
    const comprimido = new Blob(['comprimido'])
    comprimirImagen.mockResolvedValueOnce(comprimido)
    const wrapper = mount(CapturaEvidencia, { props: { minFotos: 1, maxFotos: 3 } })

    await dispararSeleccion(wrapper, [archivoDe('foto.jpg')])
    await wrapper.vm.$nextTick()

    const fotos = wrapper.emitted('update:fotos').at(-1)[0]
    expect(fotos).toHaveLength(1)
    expect(fotos[0].archivo.name).toBe('foto.jpg')
  })

  // Regresión real reportada en producción: una actividad se creó sin
  // ninguna foto aunque el técnico sí la tomó. Causa raíz: `comprimiendo`
  // vivía solo dentro de este componente — el padre (`NuevaActividadView`)
  // no sabía que seguía en curso y dejaba tocar "Guardar" mientras la
  // compresión aún corría, armando el payload con `fotos` todavía vacío.
  // Ahora este componente también emite `update:comprimiendo` para que el
  // padre pueda deshabilitar "Guardar" en esa ventana.
  it('emite update:comprimiendo(true) al empezar a procesar y (false) al terminar', async () => {
    let resolverCompresion
    comprimirImagen.mockReturnValueOnce(
      new Promise((resolve) => {
        resolverCompresion = resolve
      }),
    )
    const wrapper = mount(CapturaEvidencia, { props: { minFotos: 1, maxFotos: 3 } })

    const disparo = dispararSeleccion(wrapper, [archivoDe('foto.jpg')])
    await wrapper.vm.$nextTick()

    // Mientras la compresión sigue pendiente, ya se avisó `true` y todavía
    // no se avisó `false` — esta es exactamente la ventana en la que antes
    // se podía tocar "Guardar" con `fotos` vacío en el padre.
    expect(wrapper.emitted('update:comprimiendo')?.[0]).toEqual([true])
    expect(wrapper.emitted('update:comprimiendo')).toHaveLength(1)

    resolverCompresion(new Blob(['ok']))
    await disparo
    await wrapper.vm.$nextTick()

    const eventos = wrapper.emitted('update:comprimiendo')
    expect(eventos.at(-1)).toEqual([false])
  })
})
