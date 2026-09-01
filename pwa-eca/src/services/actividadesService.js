// pwa-eca — servicio de actividades (ECA-013). Online en este ticket.
import { api } from './api'

export async function crearActividad(payload) {
  const { data } = await api.post('/actividades', payload)
  return data
}

export async function listarMisActividades(params = {}) {
  const { data } = await api.get('/actividades/me', { params })
  return data
}
