<!-- pwa-eca — tarjeta de actividad para el Historial (ECA-019).
     El indicador de sincronización se deriva del `estado_local` del
     outbox (§2.3) — nunca de un estado guardado en la actividad misma. -->
<script setup>
defineProps({
  actividad: { type: Object, required: true },
  // 'SINCRONIZADO' cuando ya existe en el servidor; si no, el
  // `estado_local` del outbox (PENDIENTE/SINCRONIZANDO/RECHAZADO).
  estadoSincronizacion: { type: String, required: true },
})

const ETIQUETAS = {
  SINCRONIZADO: 'Sincronizada',
  PENDIENTE: 'Sin sincronizar',
  SINCRONIZANDO: 'Sincronizando…',
  RECHAZADO: 'Rechazada',
}
</script>

<template>
  <article class="actividad-card" :class="`actividad-card--${estadoSincronizacion.toLowerCase()}`">
    <header class="actividad-card__cabecera">
      <span class="actividad-card__fecha">{{ new Date(actividad.fecha_hora).toLocaleString() }}</span>
      <span class="actividad-card__badge">{{ ETIQUETAS[estadoSincronizacion] }}</span>
    </header>
    <p class="actividad-card__descripcion">{{ actividad.descripcion }}</p>
    <p v-if="actividad.resultado" class="eca-ayuda">{{ actividad.resultado }}</p>
    <p v-if="actividad.ultimo_error" class="actividad-card__error">{{ actividad.ultimo_error }}</p>
  </article>
</template>

<style scoped>
.actividad-card {
  background: var(--eca-card);
  border-radius: var(--eca-r-md);
  padding: 0.85rem 1rem;
  box-shadow: var(--eca-shadow-card);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.actividad-card__cabecera {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.actividad-card__fecha {
  font-size: 0.8rem;
  color: var(--eca-ink-faint);
}
.actividad-card__badge {
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
.actividad-card__descripcion {
  margin: 0;
}
.actividad-card__error {
  color: var(--eca-danger);
  font-size: 0.82rem;
  margin: 0;
}
</style>
