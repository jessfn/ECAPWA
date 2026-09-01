// admin-eca — servicio de ámbitos geográficos de técnico (ECA-008).
import { api } from './api'

export async function obtenerAmbito(usuarioId) {
  const { data } = await api.get(`/usuarios/${usuarioId}/ambito`)
  return data
}

export async function reemplazarAmbito(usuarioId, municipioIds) {
  const { data } = await api.put(`/usuarios/${usuarioId}/ambito`, { municipio_ids: municipioIds })
  return data
}

export async function importarAmbitos(archivo) {
  const formData = new FormData()
  formData.append('archivo', archivo)
  const { data } = await api.post('/ambitos/importar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
