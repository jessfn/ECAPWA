// admin-eca — servicio de asignaciones directas técnico↔ECA (ECA-009).
import { api } from './api'

export async function listarAsignaciones({ tecnicoId, ecaId } = {}) {
  const { data } = await api.get('/asignaciones', { params: { tecnico_id: tecnicoId, eca_id: ecaId } })
  return data
}

export async function crearAsignacion(usuarioId, ecaId) {
  const { data } = await api.post('/asignaciones', { usuario_id: usuarioId, eca_id: ecaId })
  return data
}

export async function eliminarAsignacion(asignacionId) {
  await api.delete(`/asignaciones/${asignacionId}`)
}

export async function importarAsignaciones(archivo) {
  const formData = new FormData()
  formData.append('archivo', archivo)
  const { data } = await api.post('/asignaciones/importar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
