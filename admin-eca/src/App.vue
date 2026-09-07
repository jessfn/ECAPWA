<script setup>
// admin-eca — componente raíz. La ruta de login trae su propio fondo
// oscuro a pantalla completa (`auth.css` — mismo enfoque que `admin-pwa`):
// sin esto, el fondo morado del resto de la app se asoma en la transición.
import { computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { conectarSocketPermisos, desconectarSocketPermisos } from './services/permisosSocket'
import { primeraRutaAccesible } from './router'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const esRutaAuth = computed(() => route.name === 'login')

// Pedido explícito: si a un usuario le quitan acceso a la vista que tiene
// abierta, debe salir de ahí al instante, sin recargar el navegador — el
// WebSocket dispara `auth.cargarPerfil()`, y este watcher es quien de
// verdad reacciona al nuevo arreglo de permisos revisando la ruta activa.
watch(
  () => auth.permisos,
  () => {
    const permisoRequerido = route.meta?.requierePermiso
    if (permisoRequerido && !auth.tienePermiso(permisoRequerido)) {
      router.replace(primeraRutaAccesible(auth))
    }
  },
)

watch(
  () => auth.estaAutenticado,
  (autenticado) => {
    if (autenticado) conectarSocketPermisos()
    else desconectarSocketPermisos()
  },
)

onMounted(() => {
  if (auth.estaAutenticado) conectarSocketPermisos()
})

onBeforeUnmount(desconectarSocketPermisos)
</script>

<template>
  <div :class="{ 'auth-route': esRutaAuth }">
    <RouterView />
  </div>
</template>
