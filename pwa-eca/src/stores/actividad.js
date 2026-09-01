// pwa-eca — store de "nueva actividad" (ECA-013 + ECA-015 + ECA-016).
//
// Desde ECA-016, crear la actividad y sus evidencias **ya no llama al
// API**: se encola en `outbox_actividades`/`outbox_evidencias` (fotos como
// `Blob`, nunca base64 — corrige `02` §15). El envío real al backend lo
// hace el motor de sincronización de ECA-017.
import { defineStore } from 'pinia'
import { encolar } from '../services/outbox'
import { useOutboxStore } from './outbox'

export const useActividadStore = defineStore('actividad', {
  state: () => ({
    guardando: false,
    error: '',
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
          gps: gps || null,
        })
      } catch {
        this.error = 'No se pudo guardar la actividad localmente.'
        throw new Error('encolar_actividad_fallo')
      } finally {
        this.guardando = false
        await useOutboxStore().refrescar()
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
            gps: gps || null,
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
      return errores
    },
  },
})
