// pwa-eca — servicio de evidencias fotográficas (ECA-015). Online en este
// ticket: se sube justo después de crear la actividad.
import { api } from './api'

export async function subirEvidencia(actividadUuid, { uuid, orden, archivo, gps, capturadaEn }) {
  const formData = new FormData()
  formData.append('uuid', uuid)
  formData.append('orden', orden)
  formData.append('archivo', archivo)
  if (gps?.latitud != null) formData.append('latitud', gps.latitud)
  if (gps?.longitud != null) formData.append('longitud', gps.longitud)
  if (capturadaEn) formData.append('capturada_en', capturadaEn)

  const { data } = await api.post(`/actividades/${actividadUuid}/evidencias`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
