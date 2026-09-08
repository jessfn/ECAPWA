// admin-eca — servicio de jornadas (entrada/salida) para la vista
// "Asistencia" (admin, todos los técnicos).
import { api } from './api'

export async function listarTodasJornadas({
  tecnicoId,
  estado,
  desde,
  hasta,
  page = 1,
  pageSize = 50,
} = {}) {
  const { data } = await api.get('/jornadas/todas', {
    params: {
      tecnico_id: tecnicoId,
      estado,
      desde,
      hasta,
      page,
      page_size: pageSize,
    },
  })
  return data
}
