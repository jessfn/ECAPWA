<script setup>
// admin-eca — componente raíz. La ruta de login trae su propio fondo
// oscuro a pantalla completa (`auth.css` — mismo enfoque que `admin-pwa`):
// sin esto, el fondo morado del resto de la app se asoma en la transición.
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const esRutaAuth = computed(() => route.name === 'login')
</script>

<template>
  <div :class="{ 'auth-route': esRutaAuth }">
    <RouterView />
  </div>
</template>
