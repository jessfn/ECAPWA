// pwa-eca — llamadas HTTP de sincronización (ECA-017).
import { api } from './api'

export async function registrarDispositivo({ uuid, plataforma, userAgent }) {
  const { data } = await api.post('/sync/dispositivo', {
    uuid,
    plataforma,
    user_agent: userAgent,
  })
  return data
}

export async function push({ dispositivoUuid, jornadas, actividades }) {
  const { data } = await api.post('/sync/push', {
    dispositivo_uuid: dispositivoUuid,
    jornadas,
    actividades,
  })
  return data
}
