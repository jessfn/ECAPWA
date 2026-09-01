// pwa-eca — compresión de imágenes antes de subir evidencias (ECA-015).
//
// Copiado y adaptado de `pwasuper/src/utils/imageCompressor.js` (copia
// deliberada, no import — `AGENTS.md` regla 5: ECA nace independiente del
// código de Sembrando Vida, aunque reutilice el mismo enfoque probado).
export async function comprimirImagen(archivo, anchoMaximo = 1280, calidad = 0.6) {
  return new Promise((resolve, reject) => {
    try {
      const img = new Image()
      const objectURL = URL.createObjectURL(archivo)

      img.onload = () => {
        URL.revokeObjectURL(objectURL)

        let ancho = img.width
        let alto = img.height
        if (ancho > anchoMaximo) {
          alto = Math.floor(alto * (anchoMaximo / ancho))
          ancho = anchoMaximo
        }

        const canvas = document.createElement('canvas')
        canvas.width = ancho
        canvas.height = alto
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, ancho, alto)

        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(new Blob([blob], { type: 'image/jpeg' }))
            } else {
              reject(new Error('No se pudo comprimir la imagen.'))
            }
          },
          'image/jpeg',
          calidad,
        )
      }

      img.onerror = () => {
        URL.revokeObjectURL(objectURL)
        reject(new Error('No se pudo cargar la imagen para comprimirla.'))
      }

      img.src = objectURL
    } catch (error) {
      reject(error)
    }
  })
}

export function blobAArchivo(blob, nombreArchivo) {
  return new File([blob], nombreArchivo, { type: 'image/jpeg', lastModified: Date.now() })
}
