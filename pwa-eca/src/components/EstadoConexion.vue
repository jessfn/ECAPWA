<!-- pwa-eca — indicador de conectividad (ECA-011). Solo UX. -->
<script setup>
import { useConectividad } from '../services/conectividad'

const { enLinea } = useConectividad()
</script>

<template>
  <span class="eca-badge" :class="{ 'eca-badge--offline': !enLinea }" role="status">
    <span class="eca-badge__punto" />
    {{ enLinea ? 'En línea' : 'Sin conexión' }}
  </span>
</template>

<style scoped>
.eca-badge--offline {
  background: rgba(245, 196, 81, 0.25);
  color: var(--eca-gold);
}
</style>
