// admin-eca — servicio de consulta de actividades (ECA-019).
//
// Descargas (CSV y evidencias) requieren `Authorization`, así que no se
// puede usar un `<a href>` plano — se piden como `blob` con el mismo
// cliente `api` (que ya adjunta el token) y se disparan como descarga.
import { api } from './api'

export async function listarActividades({
  tecnicoId,
  ecaId,
  municipioId,
  tipoActividadId,
  temaId,
  estadoGps,
  desde,
  hasta,
  page = 1,
  pageSize = 50,
} = {}) {
  const { data } = await api.get('/actividades', {
    params: {
      tecnico_id: tecnicoId,
      eca_id: ecaId,
      municipio_id: municipioId,
      tipo_actividad_id: tipoActividadId,
      tema_id: temaId,
      estado_gps: estadoGps,
      desde,
      hasta,
      page,
      page_size: pageSize,
    },
  })
  return data
}

export async function obtenerActividad(uuid) {
  const { data } = await api.get(`/actividades/${uuid}`)
  return data
}

function descargarBlob(blob, nombreArchivo) {
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombreArchivo
  document.body.appendChild(enlace)
  enlace.click()
  enlace.remove()
  URL.revokeObjectURL(url)
}

export async function exportarCsv({
  tecnicoId,
  ecaId,
  municipioId,
  tipoActividadId,
  temaId,
  estadoGps,
  desde,
  hasta,
} = {}) {
  const { data } = await api.get('/actividades/exportar', {
    params: {
      tecnico_id: tecnicoId,
      eca_id: ecaId,
      municipio_id: municipioId,
      tipo_actividad_id: tipoActividadId,
      tema_id: temaId,
      estado_gps: estadoGps,
      desde,
      hasta,
    },
    responseType: 'blob',
  })
  descargarBlob(data, 'actividades.csv')
}

export async function descargarEvidencia(evidenciaId, nombreArchivo) {
  const { data } = await api.get(`/evidencias/${evidenciaId}`, { responseType: 'blob' })
  descargarBlob(data, nombreArchivo || `evidencia-${evidenciaId}`)
}

export async function urlVistaPreviaEvidencia(evidenciaId) {
  const { data } = await api.get(`/evidencias/${evidenciaId}`, { responseType: 'blob' })
  return URL.createObjectURL(data)
}
