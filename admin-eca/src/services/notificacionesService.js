// admin-eca — servicio de notificaciones (envío, programación, historial y
// subida de medios por partes: Cloudflare corta cada petición a 100 MB y el
// video llega a 200 MB).
import { api } from './api'

export const MAX_VIDEO = 200 * 1024 * 1024
export const MAX_IMAGEN = 25 * 1024 * 1024

export async function listarNotificaciones({ estado, texto } = {}) {
  const { data } = await api.get('/notificaciones', { params: { estado, texto } })
  return data
}

export async function crearNotificacion(cuerpo) {
  const { data } = await api.post('/notificaciones', cuerpo)
  return data
}

export async function retirarNotificacion(uuid) {
  const { data } = await api.post(`/notificaciones/${uuid}/retirar`)
  return data
}

export async function buscarDestinatarios(texto) {
  const { data } = await api.get('/notificaciones/destinatarios', { params: { texto } })
  return data
}

// Sube un archivo en partes (con 3 reintentos por parte). `onProgreso(0..1)`.
export async function subirMedio(archivo, onProgreso = () => {}) {
  const { data: inicio } = await api.post('/notificaciones/subidas', {
    nombre: archivo.name || 'archivo',
    mime: archivo.type || 'application/octet-stream',
    tamano: archivo.size,
    total_partes: Math.max(1, Math.ceil(archivo.size / (8 * 1024 * 1024))),
  })
  const tamanoParte = Math.min(inicio.tamano_parte_max, 8 * 1024 * 1024)
  const totalPartes = Math.max(1, Math.ceil(archivo.size / tamanoParte))
  // El servidor fijó `total_partes` con 8 MB; si difiere, usar el mismo cálculo.
  for (let i = 0; i < totalPartes; i++) {
    const trozo = archivo.slice(i * tamanoParte, (i + 1) * tamanoParte)
    let intento = 0
    for (;;) {
      try {
        await api.put(`/notificaciones/subidas/${inicio.subida_id}/partes/${i}`, trozo, {
          headers: { 'Content-Type': 'application/octet-stream' },
          timeout: 0,
          onUploadProgress: (e) => onProgreso((i + (e.total ? e.loaded / e.total : 0)) / totalPartes),
        })
        break
      } catch (error) {
        if (++intento >= 3 || error.response?.status === 422 || error.response?.status === 413) throw error
        await new Promise((r) => setTimeout(r, 800 * intento))
      }
    }
    onProgreso((i + 1) / totalPartes)
  }
  const { data } = await api.post(`/notificaciones/subidas/${inicio.subida_id}/finalizar`)
  return data
}
