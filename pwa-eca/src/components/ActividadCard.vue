<!-- pwa-eca — tarjeta de actividad para el Historial (ECA-019). Rediseño
     calcado del historial de pwasuper: círculo de ícono a la izquierda
     (color según modalidad — verde "Campo", ámbar "Gabinete"), hora en
     grande, tipo de actividad + modalidad, descripción, coordenadas y
     el indicador de sincronización (exclusivo del outbox local, §2.3 —
     nunca un estado guardado en la actividad misma). -->
<script setup>
import AuthIcon from './auth/AuthIcon.vue'

const props = defineProps({
  actividad: { type: Object, required: true },
  // 'SINCRONIZADO' cuando ya existe en el servidor; si no, el
  // `estado_local` del outbox (PENDIENTE/SINCRONIZANDO/RECHAZADO).
  estadoSincronizacion: { type: String, required: true },
  modalidadNombre: { type: String, default: null },
  tipoActividadNombre: { type: String, default: null },
})

const ETIQUETAS = {
  SINCRONIZADO: 'Sincronizada',
  PENDIENTE: 'Sin sincronizar',
  SINCRONIZANDO: 'Sincronizando…',
  RECHAZADO: 'Rechazada',
}

// "Campo" (trabajo en terreno) vs "Gabinete" (oficina) — mismo criterio
// visual que pwasuper (verde/naranja), decidido por el NOMBRE de la
// modalidad porque el id varía entre entornos/semillas de catálogo.
const esGabinete = props.modalidadNombre?.toLowerCase().includes('gabinete')

const hora = new Date(props.actividad.fecha_hora).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })

const gps = props.actividad.gps ?? {
  latitud: props.actividad.latitud,
  longitud: props.actividad.longitud,
  precision_gps_m: props.actividad.precision_gps_m,
  estado_gps: props.actividad.estado_gps,
}
const coords = gps?.latitud != null && gps?.longitud != null ? `${gps.latitud.toFixed(5)}, ${gps.longitud.toFixed(5)}` : null
</script>

<template>
  <article class="actividad-card" :class="`actividad-card--${estadoSincronizacion.toLowerCase()}`">
    <div class="actividad-card__icono" :class="esGabinete ? 'actividad-card__icono--gabinete' : 'actividad-card__icono--campo'">
      <AuthIcon :name="esGabinete ? 'briefcase' : 'leaf'" />
    </div>

    <div class="actividad-card__cuerpo">
      <header class="actividad-card__cabecera">
        <span class="actividad-card__hora">{{ hora }}</span>
        <span class="actividad-card__badge">{{ ETIQUETAS[estadoSincronizacion] }}</span>
      </header>

      <p v-if="tipoActividadNombre || modalidadNombre" class="actividad-card__tipo">
        {{ tipoActividadNombre }}<template v-if="tipoActividadNombre && modalidadNombre"> · </template>{{ modalidadNombre }}
      </p>

      <p class="actividad-card__descripcion">{{ actividad.descripcion }}</p>
      <p v-if="actividad.resultado" class="eca-ayuda">{{ actividad.resultado }}</p>

      <p v-if="coords" class="actividad-card__coords">
        <AuthIcon name="map-pin" /> {{ coords }}
      </p>

      <p v-if="actividad.ultimo_error" class="actividad-card__error">{{ actividad.ultimo_error }}</p>
    </div>
  </article>
</template>

<style scoped>
.actividad-card {
  display: flex;
  gap: 0.75rem;
  background: var(--eca-card);
  border-radius: var(--eca-r-md);
  padding: 0.85rem 1rem;
  box-shadow: var(--eca-shadow-card);
}
.actividad-card__icono {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.actividad-card__icono svg {
  width: 1.2rem;
  height: 1.2rem;
}
.actividad-card__icono--campo {
  background: linear-gradient(160deg, #30d158 0%, #16a34a 100%);
}
.actividad-card__icono--gabinete {
  background: linear-gradient(160deg, #ff9500 0%, #d97706 100%);
}

.actividad-card__cuerpo {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.actividad-card__cabecera {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.actividad-card__hora {
  font-size: 1.05rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--eca-ink);
}
.actividad-card__badge {
  flex-shrink: 0;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--eca-surface);
  color: var(--eca-ink-soft);
}
.actividad-card--sincronizado .actividad-card__badge {
  background: var(--eca-green-100);
  color: var(--eca-green-800);
}
.actividad-card--rechazado .actividad-card__badge {
  background: var(--eca-danger-bg);
  color: var(--eca-danger);
}
.actividad-card__tipo {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--eca-ink-soft);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.actividad-card__descripcion {
  margin: 0;
}
.actividad-card__coords {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.68rem;
  color: var(--eca-ink-faint);
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
}
.actividad-card__coords svg {
  width: 11px;
  height: 11px;
  flex-shrink: 0;
}
.actividad-card__error {
  color: var(--eca-danger);
  font-size: 0.82rem;
  margin: 0;
}
</style>
