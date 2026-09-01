// pwa-eca — pruebas de utilidades de imagen (ECA-015).
// `comprimirImagen` depende de <canvas>/`Image`, que jsdom no implementa
// de verdad (sin un backend de canvas) — se prueba manualmente en el
// dispositivo (ver criterios de aceptación del ticket). Aquí solo se
// cubre la parte pura y determinista: `blobAArchivo`.
import { describe, it, expect } from 'vitest'
import { blobAArchivo } from '../src/services/imagen'

describe('blobAArchivo', () => {
  it('produce un File con el nombre y tipo esperado', () => {
    const blob = new Blob(['contenido'], { type: 'image/jpeg' })

    const archivo = blobAArchivo(blob, 'foto.jpg')

    expect(archivo.name).toBe('foto.jpg')
    expect(archivo.type).toBe('image/jpeg')
    expect(archivo instanceof File).toBe(true)
  })
})
