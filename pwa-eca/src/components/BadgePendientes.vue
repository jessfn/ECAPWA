<!-- pwa-eca — contador de pendientes del outbox (ECA-016). -->
<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useOutboxStore } from '../stores/outbox'

const outbox = useOutboxStore()

onMounted(() => {
  outbox.refrescar()
})

defineExpose({ refrescar: outbox.refrescar })
</script>

<template>
  <RouterLink :to="{ name: 'sincronizacion' }" class="eca-badge badge-pendientes" :class="{ 'badge-pendientes--activo': outbox.pendientes }">
    <span class="eca-badge__punto" />
    Pendientes
    <span v-if="outbox.pendientes" class="badge-pendientes__contador">{{ outbox.pendientes }}</span>
  </RouterLink>
</template>

<style scoped>
.badge-pendientes {
  text-decoration: none;
}
.badge-pendientes--activo {
  background: rgba(245, 196, 81, 0.28);
  color: var(--eca-gold);
}
.badge-pendientes__contador {
  background: var(--eca-gold);
  color: var(--eca-green-950);
  border-radius: 999px;
  padding: 0 0.4rem;
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1.4;
}
</style>
