// pwa-eca — store de jornada (ECA-012 + ECA-014 + ECA-016).
//
// Desde ECA-016, iniciar/cerrar jornada **ya no llaman al API**: escriben
// primero en el outbox local (write-through) — la sincronización real con
// el backend la hace el motor de ECA-017. Encolar no exige `access_token`
// vigente, solo sesión local offline (§2.2), porque no toca la red.
import { defineStore } from 'pinia'
import { capturarGps } from '../services/gps'
import { encolar, actualizar, listar, reemplazar } from '../services/outbox'
import { useOutboxStore } from './outbox'
import { sincronizarOportunista } from '../services/sync'
import { obtenerJornadaDeHoy } from '../services/jornadasService'
import { asegurarSesionDeServidor } from '../services/sesionServidor'
import { useAuthStore } from './auth'

const TIENDA = 'outbox_jornadas'

function fechaLocal(iso) {
  return iso?.slice(0, 10)
}

function gpsDeRemota(lat, lon, precision, estado) {
  if (lat == null && lon == null && !estado) return null
  return { latitud: lat, longitud: lon, precision_gps_m: precision, estado_gps: estado }
}

// El servidor es la verdad para "¿ya inicié/cerré mi jornada de hoy?" —
// si este dispositivo nunca registró nada localmente (p. ej. se inició
// desde otro dispositivo/navegador), esto lo hidrata para que el resto
// de la app (bloqueo de Jornada/Actividades) refleje la realidad.
function remotaALocal(remota) {
  return {
    uuid: remota.uuid,
    inicio_en: remota.inicio_en,
    gps_inicio: gpsDeRemota(
      remota.latitud_inicio,
      remota.longitud_inicio,
      remota.precision_gps_inicio_m,
      remota.estado_gps_inicio,
    ),
    fin_en: remota.fin_en,
    gps_fin: remota.fin_en
      ? gpsDeRemota(remota.latitud_fin, remota.longitud_fin, remota.precision_gps_fin_m, remota.estado_gps_fin)
      : null,
    estado_local: 'SINCRONIZADO',
    intentos: 0,
    ultimo_error: null,
    encolado_en: remota.inicio_en,
  }
}

export const useJornadaStore = defineStore('jornada', {
  state: () => ({
    actual: null,
    cargando: false,
    error: '',
  }),

  getters: {
    abierta: (state) => Boolean(state.actual) && !state.actual.fin_en,
  },

  actions: {
    async cargarHoy() {
      this.cargando = true
      this.error = ''
      try {
        const todas = await listar(TIENDA)
        const hoy = fechaLocal(new Date().toISOString())
        let local =
          todas
            .filter((j) => fechaLocal(j.inicio_en) === hoy)
            .sort((a, b) => (a.encolado_en < b.encolado_en ? 1 : -1))[0] || null

        // El outbox local solo sabe lo que se registró *en este
        // dispositivo* — si el técnico ya inició (o cerró) su jornada
        // desde otro dispositivo/navegador, este nunca se entera por sí
        // solo. Se contrasta con el servidor (mejor esfuerzo: sin red o
        // sin sesión, se sigue con lo local, nunca se pierde nada).
        // Antes se llamaba a `/jornadas/me/hoy` directamente, sin fijarse
        // si el `access_token` ya estaba vencido — eso garantizaba un 401
        // visible en consola (aunque el interceptor de `api.js` lo
        // reintentara solo tras refrescar). Al asegurar la sesión primero
        // se evita ese roundtrip predecible.
        if (navigator.onLine && (await asegurarSesionDeServidor(useAuthStore()))) {
          try {
            const remota = await obtenerJornadaDeHoy()
            if (remota && (!local || local.uuid !== remota.uuid || (remota.fin_en && !local.fin_en))) {
              local = await reemplazar(TIENDA, remotaALocal(remota))
              await useOutboxStore().refrescar()
            }
          } catch {
            // sin red real, sesión vencida entre medio, etc. — se sigue con lo local
          }
        }

        this.actual = local
      } catch {
        this.error = 'No se pudo consultar la jornada de hoy.'
      } finally {
        this.cargando = false
      }
    },

    // `gpsPrevio`: si la pantalla ya capturó el GPS (p. ej. en el modal de
    // confirmación con animación), se reutiliza en vez de pedirlo de nuevo.
    // Se copia a un objeto plano: si viene de un `ref()` de Vue, es un
    // Proxy reactivo y `IDBObjectStore.put` no puede clonarlo
    // (`DataCloneError`) — reventaba en silencio, atrapado por el catch.
    async iniciar(gpsPrevio = null) {
      if (this.actual) return
      this.cargando = true
      this.error = ''
      try {
        const gps = gpsPrevio ? { ...gpsPrevio } : await capturarGps()
        this.actual = await encolar(TIENDA, {
          uuid: crypto.randomUUID(),
          inicio_en: new Date().toISOString(),
          gps_inicio: gps,
          fin_en: null,
          gps_fin: null,
        })
        await useOutboxStore().refrescar()
        sincronizarOportunista()
      } catch {
        this.error = 'No se pudo iniciar la jornada.'
      } finally {
        this.cargando = false
      }
    },

    async cerrar(gpsPrevio = null) {
      if (!this.actual) return
      this.cargando = true
      this.error = ''
      try {
        const gps = gpsPrevio ? { ...gpsPrevio } : await capturarGps()
        this.actual = await actualizar(TIENDA, this.actual.uuid, {
          fin_en: new Date().toISOString(),
          gps_fin: gps,
          // Se vuelve a marcar PENDIENTE: aunque ya se hubiera intentado
          // sincronizar el inicio, el cierre es información nueva que el
          // motor de sync (ECA-017) todavía no ha enviado.
          estado_local: 'PENDIENTE',
        })
        await useOutboxStore().refrescar()
        sincronizarOportunista()
      } catch {
        this.error = 'No se pudo terminar la jornada.'
      } finally {
        this.cargando = false
      }
    },
  },
})
