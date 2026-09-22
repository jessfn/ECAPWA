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

// Detalle completo (con la lista de evidencias) de una actividad propia —
// para el visor de fotos del Historial. El mismo endpoint que usa
// admin-eca; el backend permite ver el detalle de una actividad AJENA solo
// con `ver_todas`, pero la PROPIA siempre se puede ver con `ver_propias`.
export async function obtenerActividad(uuid) {
  const { data } = await api.get(`/actividades/${uuid}`)
  return data
}

// Miniatura de evidencia para el Historial (pedido explícito) — mismo
// patrón que admin-eca: la descarga siempre pasa por auth+permiso (nunca
// una URL estática pública), así que se pide como blob y se expone como
// Object URL. Quien la use debe revocarla (`URL.revokeObjectURL`) cuando
// ya no la necesite, para no acumular memoria.
export async function urlVistaPreviaEvidencia(evidenciaId) {
  const { data } = await api.get(`/evidencias/${evidenciaId}`, { responseType: 'blob' })
  return URL.createObjectURL(data)
}
