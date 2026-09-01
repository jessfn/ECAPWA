// admin-eca — servicio de ECA y su importación masiva (ECA-007).
import { api } from './api'

export async function listarEcas({ estadoId, municipioId, q, activo, page = 1, pageSize = 50 } = {}) {
  const { data } = await api.get('/ecas', {
    params: { estado_id: estadoId, municipio_id: municipioId, q, activo, page, page_size: pageSize },
  })
  return data
}

export async function crearEca(payload) {
  const { data } = await api.post('/ecas', payload)
  return data
}

export async function editarEca(ecaId, payload) {
  const { data } = await api.patch(`/ecas/${ecaId}`, payload)
  return data
}

/** Paso 1: sube el archivo, valida por fila, NO escribe nada todavía. */
export async function iniciarImportacion(archivo, columnaIdentificador) {
  const formData = new FormData()
  formData.append('archivo', archivo)
  if (columnaIdentificador) {
    formData.append('columna_identificador', columnaIdentificador)
  }
  const { data } = await api.post('/ecas/importar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function obtenerLote(loteUuid) {
  const { data } = await api.get(`/ecas/importar/${loteUuid}`)
  return data
}

/** Paso 2: confirma el lote ya validado — upsert real por clave_fuente. */
export async function confirmarImportacion(loteUuid) {
  const { data } = await api.post(`/ecas/importar/${loteUuid}/confirmar`)
  return data
}
