// admin-eca — servicio de catálogos geográficos (ECA-006).
import { api } from './api'

export async function listarEstados({ activo } = {}) {
  const { data } = await api.get('/geo/estados', { params: { activo } })
  return data
}

export async function listarMunicipios(estadoId, { activo, q } = {}) {
  const { data } = await api.get('/geo/municipios', { params: { estado_id: estadoId, activo, q } })
  return data
}

export async function actualizarEstadoActivo(estadoId, activo) {
  const { data } = await api.patch(`/geo/estados/${estadoId}`, { activo })
  return data
}

export async function actualizarMunicipioActivo(municipioId, activo) {
  const { data } = await api.patch(`/geo/municipios/${municipioId}`, { activo })
  return data
}
