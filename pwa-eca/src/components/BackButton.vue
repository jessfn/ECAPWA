<!-- pwa-eca — botón "volver" reutilizable. Antes cada pantalla tenía un
     `<RouterLink>← Volver</RouterLink>` de texto plano; esto reemplaza los
     6 usos por un botón consistente, con ícono y micro-animación al tacto. -->
<script setup>
import { useRouter } from 'vue-router'
import AuthIcon from './auth/AuthIcon.vue'

defineProps({
  a: { type: Object, default: () => ({ name: 'inicio' }) },
  texto: { type: String, default: 'Volver' },
})
</script>

<template>
  <RouterLink :to="a" class="eca-volver">
    <AuthIcon name="arrow-left" />
    <span>{{ texto }}</span>
  </RouterLink>
</template>

<style scoped>
.eca-volver {
  margin-bottom: 0.85rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--eca-green-700);
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  padding: 0.5rem 0.9rem 0.5rem 0.6rem;
  border-radius: 999px;
  background: var(--eca-surface);
  border: 1px solid var(--eca-surface-border);
  transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.eca-volver svg {
  width: 16px;
  height: 16px;
  transition: transform 0.15s ease;
}
.eca-volver:hover {
  background: var(--eca-green-100);
  box-shadow: 0 2px 8px rgba(21, 128, 61, 0.12);
}
.eca-volver:hover svg {
  transform: translateX(-2px);
}
.eca-volver:active {
  transform: scale(0.96);
}
</style>
