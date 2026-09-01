// admin-eca — servicio de catálogos de actividad (ECA-010).
import { api } from './api'

const RUTA_POR_TIPO = {
  modalidades: '/catalogos/modalidades',
  'tipos-actividad': '/catalogos/tipos-actividad',
  temas: '/catalogos/temas',
  subtemas: '/catalogos/subtemas',
  'sistemas-productivos': '/catalogos/sistemas-productivos',
}

export async function listarCatalogo(tipo, { todos = true, temaId = null } = {}) {
  const params = { todos }
  if (tipo === 'subtemas' && temaId) params.tema_id = temaId
  const { data } = await api.get(RUTA_POR_TIPO[tipo], { params })
  return data
}

export async function editarItemCatalogo(tipo, id, cambios) {
  const { data } = await api.patch(`/catalogos/${tipo}/${id}`, cambios)
  return data
}

export async function crearSubtema({ temaId, clave, nombre, orden = 0 }) {
  const { data } = await api.post('/catalogos/subtemas', {
    tema_id: temaId,
    clave,
    nombre,
    orden,
  })
  return data
}
