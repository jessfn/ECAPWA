// pwa-eca — servicio de jornadas (ECA-012). Online en este ticket; la
// integración con el outbox llega en ECA-016.
import { api } from './api'

export async function iniciarJornada({ uuid, inicioEn, gps }) {
  const { data } = await api.post('/jornadas', { uuid, inicio_en: inicioEn, gps })
  return data
}

export async function cerrarJornada(uuid, { finEn, gps }) {
  const { data } = await api.patch(`/jornadas/${uuid}/cerrar`, { fin_en: finEn, gps })
  return data
}

export async function obtenerJornadaDeHoy() {
  const { data } = await api.get('/jornadas/me/hoy')
  return data
}

// Historial (ECA-019): el backend ya expone `GET /jornadas` filtrado por
// el usuario del token (`jornadas.ver_propias`) — no hacía falta ningún
// endpoint nuevo, solo consumirlo desde el frontend.
export async function listarMisJornadas() {
  const { data } = await api.get('/jornadas')
  return data
}
