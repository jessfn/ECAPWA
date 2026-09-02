// pwa-eca — store de jornada (ECA-012 + ECA-014 + ECA-016).
//
// Desde ECA-016, iniciar/cerrar jornada **ya no llaman al API**: escriben
// primero en el outbox local (write-through) — la sincronización real con
// el backend la hace el motor de ECA-017. Encolar no exige `access_token`
// vigente, solo sesión local offline (§2.2), porque no toca la red.
import { defineStore } from 'pinia'
import { capturarGps } from '../services/gps'
import { encolar, actualizar, listar } from '../services/outbox'
import { useOutboxStore } from './outbox'
import { sincronizarOportunista } from '../services/sync'

const TIENDA = 'outbox_jornadas'

function fechaLocal(iso) {
  return iso?.slice(0, 10)
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
        this.actual =
          todas
            .filter((j) => fechaLocal(j.inicio_en) === hoy)
            .sort((a, b) => (a.encolado_en < b.encolado_en ? 1 : -1))[0] || null
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
        const gps = gpsPrevio ? { ...gpsPrevio } : await capturarGps({ intentos: 1 })
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
        const gps = gpsPrevio ? { ...gpsPrevio } : await capturarGps({ intentos: 1 })
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
