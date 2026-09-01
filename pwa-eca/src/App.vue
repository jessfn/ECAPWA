<!-- pwa-eca — componente raíz. Las rutas de autenticación (login/registro)
     traen su propio fondo oscuro a pantalla completa (`auth.css` — mismo
     enfoque que `pwasuper`): sin esto, el fondo claro del resto de la app se
     asoma durante la transición entre pantallas. Fuera de esas rutas, si hay
     sesión, se muestra la barra superior + menú hamburguesa (`AppHeader`,
     paridad de diseño pedida con `pwasuper`) para que todas las pantallas
     compartan la misma navegación — antes solo "Inicio" tenía un header
     propio y el resto eran pantallas sin salida. El fondo de la app ya
     logueada es blanco desvanecido a verde manzana suave, con manchas
     "liquid glass" difuminadas detrás del contenido (pedido explícito). -->
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppHeader from './components/AppHeader.vue'

const route = useRoute()
const auth = useAuthStore()
const esRutaAuth = computed(() => ['login', 'registro'].includes(route.name))
const mostrarHeader = computed(() => !esRutaAuth.value && auth.estaAutenticado)
</script>

<template>
  <div :class="{ 'auth-route': esRutaAuth }">
    <div v-if="!esRutaAuth" class="app-liquid-bg" aria-hidden="true">
      <span class="app-liquid-bg__mancha app-liquid-bg__mancha--1"></span>
      <span class="app-liquid-bg__mancha app-liquid-bg__mancha--2"></span>
      <span class="app-liquid-bg__mancha app-liquid-bg__mancha--3"></span>
    </div>

    <AppHeader v-if="mostrarHeader" />
    <main :class="{ 'app-main--con-header': mostrarHeader }">
      <RouterView />
    </main>
  </div>
</template>

<style>
.app-main--con-header {
  /* El header creció con la barra de "En línea"/"Sin conexión" pegada
     debajo; se suma el alto aproximado de esa barra (~34px). */
  padding-top: calc(98px + env(safe-area-inset-top, 0px));
  position: relative;
  z-index: 1;
}

.app-liquid-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  /* Verde manzana suave con blanco, en degradado — pedido explícito: antes
     el blanco dominaba demasiado y el verde casi no se notaba. */
  background: linear-gradient(160deg, #ffffff 0%, #eafaf1 45%, #d3f3e0 100%);
}
.app-liquid-bg__mancha {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.7;
  will-change: transform;
}
.app-liquid-bg__mancha--1 {
  width: 60vmax;
  height: 60vmax;
  top: -22vmax;
  right: -18vmax;
  background: radial-gradient(circle, rgba(74, 222, 128, 0.6) 0%, transparent 70%);
  animation: app-liquid-drift-1 26s ease-in-out infinite;
}
.app-liquid-bg__mancha--2 {
  width: 50vmax;
  height: 50vmax;
  bottom: -20vmax;
  left: -16vmax;
  background: radial-gradient(circle, rgba(134, 239, 172, 0.55) 0%, transparent 70%);
  animation: app-liquid-drift-2 30s ease-in-out infinite;
}
.app-liquid-bg__mancha--3 {
  width: 34vmax;
  height: 34vmax;
  top: 38vh;
  left: 50vw;
  transform: translateX(-50%);
  background: radial-gradient(circle, rgba(187, 247, 208, 0.65) 0%, transparent 70%);
  animation: app-liquid-drift-3 22s ease-in-out infinite;
}
@keyframes app-liquid-drift-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-4vmax, 3vmax) scale(1.08); }
}
@keyframes app-liquid-drift-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(3vmax, -4vmax) scale(1.1); }
}
@keyframes app-liquid-drift-3 {
  0%, 100% { transform: translate(-50%, 0) scale(1); opacity: 0.6; }
  50% { transform: translate(-50%, 2vmax) scale(1.15); opacity: 0.4; }
}
@media (prefers-reduced-motion: reduce) {
  .app-liquid-bg__mancha {
    animation: none;
  }
}
</style>
