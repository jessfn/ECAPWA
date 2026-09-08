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

// `actualizarEstadoActivo`/`actualizarMunicipioActivo` (PATCH activar/
// desactivar) vivían solo en `GeografiaView.vue`, retirada del panel —
// se quitan de aquí junto con ella. El endpoint sigue existiendo en el
// backend (protegido por `geo.gestionar`, ahora desactivado) por si se
// reactiva la gestión de geografía más adelante.
