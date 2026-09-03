// pwa-eca — store de "nueva actividad" (ECA-013 + ECA-015 + ECA-016).
//
// Desde ECA-016, crear la actividad y sus evidencias **ya no llama al
// API**: se encola en `outbox_actividades`/`outbox_evidencias` (fotos como
// `Blob`, nunca base64 — corrige `02` §15). El envío real al backend lo
// hace el motor de sincronización de ECA-017.
import { defineStore } from 'pinia'
import { encolar } from '../services/outbox'
import { useOutboxStore } from './outbox'
import { sincronizar } from '../services/sync'
import { useAuthStore } from './auth'

export const useActividadStore = defineStore('actividad', {
  state: () => ({
    guardando: false,
    error: '',
    // Resultado del intento de sincronización disparado tras encolar — la
    // pantalla lo usa para saber si debe avisar "sin señal" o "ya se
    // sincronizó" en vez de asumir siempre que no hay conexión (ECA-013).
    ultimoSync: null,
  }),

  actions: {
    async crear({
      jornadaUuid,
      ecaId,
      modalidadId,
      tipoActividadId,
      temaId,
      subtemaId,
      sistemaProductivoId,
      descripcion,
      resultado,
      numParticipantes,
      requiereSeguimiento,
      fechaProximoSeguimiento,
      gps,
    }) {
      this.guardando = true
      this.error = ''
      try {
        return await encolar('outbox_actividades', {
          uuid: crypto.randomUUID(),
          jornada_uuid: jornadaUuid,
          eca_id: ecaId,
          modalidad_id: modalidadId,
          tipo_actividad_id: tipoActividadId,
          tema_id: temaId,
          subtema_id: subtemaId,
          sistema_productivo_id: sistemaProductivoId,
          descripcion,
          resultado,
          fecha_hora: new Date().toISOString(),
          num_participantes: numParticipantes,
          requiere_seguimiento: requiereSeguimiento,
          fecha_proximo_seguimiento: fechaProximoSeguimiento,
          // Copia a un objeto plano: igual que en `stores/jornada.js`, un
          // `gps` que viene de un `ref()` de Vue al que se le asignó un
          // objeto queda envuelto en un Proxy reactivo — `IDBObjectStore.put`
          // no puede clonarlo (`DataCloneError`) y esto reventaba en
          // silencio, atrapado por el catch de abajo como "no se pudo
          // guardar la actividad localmente" en TODOS los intentos con GPS.
          gps: gps ? { ...gps } : null,
        })
      } catch {
        this.error = 'No se pudo guardar la actividad localmente.'
        throw new Error('encolar_actividad_fallo')
      } finally {
        this.guardando = false
        await useOutboxStore().refrescar()
        this.ultimoSync = await sincronizar(useAuthStore()).catch(() => ({ ok: false, motivo: 'error_red' }))
      }
    },

    // Encola cada foto ya comprimida (`CapturaEvidencia`) en
    // `outbox_evidencias`, referenciando la actividad por su `uuid` de
    // cliente. Mejor esfuerzo por foto: si una falla al encolar (cuota de
    // almacenamiento agotada, por ejemplo), se reporta pero no detiene las
    // demás — la actividad ya quedó encolada de todos modos.
    async encolarEvidencias(actividadUuid, fotos, gps) {
      const errores = []
      for (let i = 0; i < fotos.length; i += 1) {
        const foto = fotos[i]
        try {
          await encolar('outbox_evidencias', {
            uuid: crypto.randomUUID(),
            actividad_uuid: actividadUuid,
            orden: i + 1,
            archivo: foto.archivo, // Blob, nunca base64
            gps: gps ? { ...gps } : null,
            capturada_en: new Date().toISOString(),
          })
        } catch {
          errores.push(foto.id)
        }
      }
      if (errores.length) {
        this.error = `${errores.length} de ${fotos.length} fotos no se pudieron guardar localmente.`
      }
      await useOutboxStore().refrescar()
      this.ultimoSync = await sincronizar(useAuthStore()).catch(() => ({ ok: false, motivo: 'error_red' }))
      return errores
    },
  },
})
