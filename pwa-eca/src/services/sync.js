// pwa-eca — motor de sincronización (ECA-017).
//
// Solo actúa con red **y** con sesión de servidor válida (recuperable con
// `refresh`); la captura offline (escribir en el outbox, ECA-016) nunca
// pasa por aquí. Si no se puede recuperar la sesión, el outbox queda
// intacto — nunca se pierde nada por no poder sincronizar.
import { listar, marcarEstado } from './outbox'
import { registrarDispositivo, push } from './syncPushService'
import { subirEvidencia } from './evidenciasService'
import { ejecutarPull } from './bootstrap'
import { useAuthStore } from '../stores/auth'

const CLAVE_DISPOSITIVO = 'eca_tecnico_dispositivo_uuid'
const ESTADOS_A_ENVIAR = new Set(['PENDIENTE', 'RECHAZADO'])
const MAX_INTENTOS_RED = 3

let sincronizando = false

function obtenerDispositivoUuid() {
  let uuid = localStorage.getItem(CLAVE_DISPOSITIVO)
  if (!uuid) {
    uuid = crypto.randomUUID()
    localStorage.setItem(CLAVE_DISPOSITIVO, uuid)
  }
  return uuid
}

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// Backoff exponencial con jitter: 500ms, 1s, 2s (± hasta 30%).
function backoffMs(intento) {
  const base = 500 * 2 ** intento
  const jitter = base * 0.3 * Math.random()
  return base + jitter
}

async function conReintentos(fn) {
  let ultimoError
  for (let intento = 0; intento < MAX_INTENTOS_RED; intento += 1) {
    try {
      return await fn()
    } catch (err) {
      ultimoError = err
      // Un rechazo del servidor (4xx) no es un error de red: no tiene
      // sentido reintentar, la respuesta ya llegó.
      if (err.response) throw err
      if (intento < MAX_INTENTOS_RED - 1) await esperar(backoffMs(intento))
    }
  }
  throw ultimoError
}

function aPayloadJornada(registro) {
  return {
    uuid: registro.uuid,
    inicio_en: registro.inicio_en,
    gps_inicio: registro.gps_inicio || null,
    fin_en: registro.fin_en || null,
    gps_fin: registro.gps_fin || null,
  }
}

function aPayloadActividad(registro) {
  return {
    uuid: registro.uuid,
    jornada_uuid: registro.jornada_uuid,
    eca_id: registro.eca_id ?? null,
    modalidad_id: registro.modalidad_id,
    tipo_actividad_id: registro.tipo_actividad_id,
    tema_id: registro.tema_id ?? null,
    subtema_id: registro.subtema_id ?? null,
    sistema_productivo_id: registro.sistema_productivo_id ?? null,
    descripcion: registro.descripcion,
    resultado: registro.resultado ?? null,
    fecha_hora: registro.fecha_hora,
    num_participantes: registro.num_participantes ?? null,
    requiere_seguimiento: Boolean(registro.requiere_seguimiento),
    fecha_proximo_seguimiento: registro.fecha_proximo_seguimiento ?? null,
    gps: registro.gps || null,
  }
}

async function asegurarSesionDeServidor(auth) {
  if (auth.sesionServidorValida) return true
  try {
    await auth.refrescar()
    return true
  } catch {
    return false
  }
}

async function sincronizarEvidenciasDe(actividadUuid) {
  const evidencias = (await listar('outbox_evidencias')).filter(
    (e) => e.actividad_uuid === actividadUuid && ESTADOS_A_ENVIAR.has(e.estado_local),
  )
  for (const evidencia of evidencias) {
    try {
      await conReintentos(() =>
        subirEvidencia(actividadUuid, {
          uuid: evidencia.uuid,
          orden: evidencia.orden,
          archivo: evidencia.archivo,
          gps: evidencia.gps,
          capturadaEn: evidencia.capturada_en,
        }),
      )
      await marcarEstado('outbox_evidencias', evidencia.uuid, 'SINCRONIZADO')
    } catch (err) {
      const motivo = err.response?.data?.error?.message || 'No se pudo subir la foto.'
      await marcarEstado('outbox_evidencias', evidencia.uuid, 'RECHAZADO', { ultimoError: motivo })
    }
  }
}

/** @returns {Promise<{ok: boolean, motivo?: string, aplicados: number, duplicados: number, rechazados: number}>} */
export async function sincronizar(auth) {
  if (sincronizando) {
    return { ok: false, motivo: 'ya_en_curso', aplicados: 0, duplicados: 0, rechazados: 0 }
  }
  sincronizando = true

  try {
    if (!navigator.onLine) {
      return { ok: false, motivo: 'sin_red', aplicados: 0, duplicados: 0, rechazados: 0 }
    }

    const sesionLista = await asegurarSesionDeServidor(auth)
    if (!sesionLista) {
      return { ok: false, motivo: 'sin_sesion', aplicados: 0, duplicados: 0, rechazados: 0 }
    }

    const dispositivoUuid = obtenerDispositivoUuid()
    await registrarDispositivo({
      uuid: dispositivoUuid,
      plataforma: navigator.platform || 'desconocida',
      userAgent: navigator.userAgent,
    }).catch(() => {}) // mejor esfuerzo: el push igual registra el dispositivo si falta

    const jornadasPendientes = (await listar('outbox_jornadas')).filter((j) => ESTADOS_A_ENVIAR.has(j.estado_local))
    const actividadesPendientes = (await listar('outbox_actividades')).filter((a) =>
      ESTADOS_A_ENVIAR.has(a.estado_local),
    )

    if (!jornadasPendientes.length && !actividadesPendientes.length) {
      return { ok: true, motivo: 'nada_pendiente', aplicados: 0, duplicados: 0, rechazados: 0 }
    }

    for (const j of jornadasPendientes) await marcarEstado('outbox_jornadas', j.uuid, 'SINCRONIZANDO')
    for (const a of actividadesPendientes) await marcarEstado('outbox_actividades', a.uuid, 'SINCRONIZANDO')

    let respuesta
    try {
      respuesta = await conReintentos(() =>
        push({
          dispositivoUuid,
          jornadas: jornadasPendientes.map(aPayloadJornada),
          actividades: actividadesPendientes.map(aPayloadActividad),
        }),
      )
    } catch {
      // Error de red persistente: se deja todo en SINCRONIZANDO→PENDIENTE
      // (nunca se pierde), para reintentar en el próximo disparo.
      for (const j of jornadasPendientes) await marcarEstado('outbox_jornadas', j.uuid, 'PENDIENTE')
      for (const a of actividadesPendientes) await marcarEstado('outbox_actividades', a.uuid, 'PENDIENTE')
      return { ok: false, motivo: 'error_red', aplicados: 0, duplicados: 0, rechazados: 0 }
    }

    let aplicados = 0
    let duplicados = 0
    let rechazados = 0
    const actividadesUuidPorResultado = new Map()

    for (const resultado of respuesta.resultados) {
      const esJornada = jornadasPendientes.some((j) => j.uuid === resultado.uuid)
      const tienda = esJornada ? 'outbox_jornadas' : 'outbox_actividades'

      if (resultado.resultado === 'RECHAZADO') {
        rechazados += 1
        await marcarEstado(tienda, resultado.uuid, 'RECHAZADO', { ultimoError: resultado.error })
      } else {
        if (resultado.resultado === 'APLICADO') aplicados += 1
        else duplicados += 1
        await marcarEstado(tienda, resultado.uuid, 'SINCRONIZADO')
        if (!esJornada) actividadesUuidPorResultado.set(resultado.uuid, true)
      }
    }

    // Evidencias: solo de actividades que el servidor ya confirmó
    // (APLICADO o DUPLICADO) — nunca de una actividad RECHAZADO.
    for (const actividadUuid of actividadesUuidPorResultado.keys()) {
      await sincronizarEvidenciasDe(actividadUuid)
    }

    // Pull periódico (ECA-018): aprovecha que ya hay red + sesión de
    // servidor para refrescar catálogos/ECA offline. Mejor esfuerzo — un
    // pull fallido no afecta el resultado del push, que ya se aplicó.
    ejecutarPull().catch(() => {})

    return { ok: true, aplicados, duplicados, rechazados }
  } finally {
    sincronizando = false
  }
}

let autoSyncArmado = false

/** Dispara una sincronización cuando el navegador recupera la red. */
export function armarAutoSync(auth) {
  if (autoSyncArmado) return
  autoSyncArmado = true
  window.addEventListener('online', () => {
    sincronizar(auth)
  })
}

// Antes, la única forma de disparar `sincronizar()` era el evento
// `online` del navegador o el botón manual de Sincronización — un
// técnico que nunca pierde la señal (el caso normal) nunca veía sus
// jornadas/actividades llegar al servidor sin entrar a esa pantalla y
// presionar "Sincronizar ahora" (parecía que "no se guardaba").
// `sincronizarOportunista()` se llama justo después de encolar cada
// registro y al arrancar la app: mejor esfuerzo, nunca lanza — si no
// hay red o sesión, el registro se queda igual de seguro en el outbox
// para el próximo intento.
export function sincronizarOportunista() {
  sincronizar(useAuthStore()).catch(() => {})
}

export function _reiniciarSyncParaPruebas() {
  sincronizando = false
  autoSyncArmado = false
}
