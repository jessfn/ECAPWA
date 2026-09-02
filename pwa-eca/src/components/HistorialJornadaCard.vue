<!-- pwa-eca — tarjeta de jornada (Registro de Inicio/Término) para el
     Historial (ECA-019). Diseño calcado del historial de pwasuper: una
     tarjeta dividida en dos mitades, Inicio (azul) y Término (rojo),
     cada una con su hora, ícono, nota y ubicación — o "En curso" si
     todavía no se registra el término. -->
<script setup>
import AuthIcon from './auth/AuthIcon.vue'

const props = defineProps({
  jornada: { type: Object, required: true },
})

function coordsDe(gps) {
  if (!gps || gps.latitud == null || gps.longitud == null) return null
  return `${gps.latitud.toFixed(5)}, ${gps.longitud.toFixed(5)}`
}

const horaInicio = new Date(props.jornada.inicio_en).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
const horaFin = props.jornada.fin_en
  ? new Date(props.jornada.fin_en).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
  : null
const coordsInicio = coordsDe(props.jornada.gps_inicio)
const coordsFin = coordsDe(props.jornada.gps_fin)
</script>

<template>
  <article class="historial-jornada">
    <div class="historial-jornada__mitad historial-jornada__mitad--inicio">
      <h3 class="historial-jornada__titulo">
        <AuthIcon name="login" /> Inicio
      </h3>
      <p class="historial-jornada__hora">{{ horaInicio }}</p>
      <p v-if="jornada.nota" class="historial-jornada__nota">{{ jornada.nota }}</p>
      <p v-if="coordsInicio" class="historial-jornada__coords">
        <AuthIcon name="map-pin" /> {{ coordsInicio }}
      </p>
    </div>

    <div class="historial-jornada__mitad historial-jornada__mitad--fin" :class="{ 'historial-jornada__mitad--curso': !horaFin }">
      <h3 class="historial-jornada__titulo">
        <AuthIcon name="logout" /> Término
      </h3>
      <template v-if="horaFin">
        <p class="historial-jornada__hora">{{ horaFin }}</p>
        <p v-if="jornada.nota_fin" class="historial-jornada__nota">{{ jornada.nota_fin }}</p>
        <p v-if="coordsFin" class="historial-jornada__coords">
          <AuthIcon name="map-pin" /> {{ coordsFin }}
        </p>
      </template>
      <div v-else class="historial-jornada__en-curso">
        <AuthIcon name="clock" />
        <span>En curso</span>
      </div>
    </div>
  </article>
</template>

<style scoped>
.historial-jornada {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
  background: var(--eca-card);
  border-radius: var(--eca-r-md);
  padding: 0.6rem;
  box-shadow: var(--eca-shadow-card);
}
.historial-jornada__mitad {
  border-radius: var(--eca-r-sm);
  padding: 0.65rem 0.7rem;
  border: 1.5px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.historial-jornada__mitad--inicio {
  background: rgba(10, 132, 255, 0.07);
  border-color: rgba(10, 132, 255, 0.22);
}
.historial-jornada__mitad--fin {
  background: rgba(255, 69, 58, 0.07);
  border-color: rgba(255, 69, 58, 0.22);
}
.historial-jornada__mitad--curso {
  background: var(--eca-surface);
  border-color: var(--eca-surface-border);
  align-items: center;
  justify-content: center;
}

.historial-jornada__titulo {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.historial-jornada__mitad--inicio .historial-jornada__titulo {
  color: #0a84ff;
}
.historial-jornada__mitad--fin .historial-jornada__titulo {
  color: #ff453a;
}
.historial-jornada__titulo svg {
  width: 13px;
  height: 13px;
}

.historial-jornada__hora {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--eca-ink);
}
.historial-jornada__nota {
  margin: 0;
  font-size: 0.78rem;
  color: var(--eca-ink-soft);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.historial-jornada__coords {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.68rem;
  color: var(--eca-ink-faint);
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
}
.historial-jornada__coords svg {
  width: 11px;
  height: 11px;
  flex-shrink: 0;
}

.historial-jornada__en-curso {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--eca-ink-faint);
  font-size: 0.8rem;
  font-weight: 600;
}
.historial-jornada__en-curso svg {
  width: 15px;
  height: 15px;
}
</style>
