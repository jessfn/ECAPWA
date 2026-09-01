<!-- pwa-eca — barra superior + menú hamburguesa de la app autenticada.
     Paridad de diseño pedida explícitamente con `pwasuper`: header verde
     fijo con zona segura (notch/isla dinámica), indicador en línea/sin
     conexión, y menú desplegable con toda la navegación real de esta app
     (antes solo `InicioView` tenía un header improvisado; el resto de
     pantallas no tenía ninguna forma de navegar entre sí). -->
<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useConectividad } from '../services/conectividad'
import AuthIcon from './auth/AuthIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { enLinea } = useConectividad()

const menuAbierto = ref(false)

const enlaces = [
  { nombre: 'inicio', etiqueta: 'Inicio', icono: 'home' },
  { nombre: 'jornada', etiqueta: 'Jornada', icono: 'calendar' },
  { nombre: 'nueva-actividad', etiqueta: 'Nueva actividad', icono: 'plus-circle' },
  { nombre: 'sincronizacion', etiqueta: 'Sincronización', icono: 'sync' },
  { nombre: 'historial', etiqueta: 'Historial', icono: 'clock' },
  { nombre: 'perfil', etiqueta: 'Mi perfil', icono: 'user' },
]

const nombreCompleto = computed(() => {
  const u = auth.usuario
  if (!u) return 'Técnico'
  return [u.nombre, u.apellido_paterno].filter(Boolean).join(' ')
})

function alternarMenu() {
  menuAbierto.value = !menuAbierto.value
}

function cerrarMenu() {
  menuAbierto.value = false
}

async function cerrarSesion() {
  cerrarMenu()
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="app-header" :class="{ 'app-header--abierto': menuAbierto }">
    <div class="app-header__fila">
      <div class="app-header__marca">
        <span class="app-header__logo">
          <AuthIcon name="leaf" />
        </span>
        <span class="app-header__marca-texto">
          <span class="app-header__nombre">ECA</span>
          <span class="app-header__usuario">{{ nombreCompleto }}</span>
        </span>
      </div>

      <div class="app-header__acciones">
        <span class="app-header__conexion" :class="{ 'app-header__conexion--offline': !enLinea }" role="status">
          <AuthIcon :name="enLinea ? 'wifi' : 'wifi-off'" />
          <span class="app-header__conexion-texto">{{ enLinea ? 'En línea' : 'Sin conexión' }}</span>
        </span>

        <button
          type="button"
          class="app-header__hamburguesa"
          :aria-expanded="menuAbierto"
          aria-label="Abrir menú"
          @click="alternarMenu"
        >
          <AuthIcon :name="menuAbierto ? 'close' : 'menu'" />
        </button>
      </div>
    </div>
  </header>

  <Transition name="menu-slide">
    <nav v-if="menuAbierto" class="app-menu">
      <RouterLink
        v-for="enlace in enlaces"
        :key="enlace.nombre"
        :to="{ name: enlace.nombre }"
        class="app-menu__enlace"
        :class="{ 'app-menu__enlace--activo': route.name === enlace.nombre }"
        @click="cerrarMenu"
      >
        <AuthIcon :name="enlace.icono" />
        <span>{{ enlace.etiqueta }}</span>
      </RouterLink>

      <div class="app-menu__separador"></div>

      <button type="button" class="app-menu__enlace app-menu__salir" @click="cerrarSesion">
        <AuthIcon name="logout" />
        <span>Cerrar sesión</span>
      </button>
    </nav>
  </Transition>

  <div v-if="menuAbierto" class="app-menu__overlay" @click="cerrarMenu"></div>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: max(8px, calc(env(safe-area-inset-top, 0px) + 8px));
  left: 8px;
  right: 8px;
  z-index: 40;
  background: var(--eca-green-900);
  color: #fff;
  border-radius: 24px;
  box-shadow: var(--eca-shadow-card);
  transition: border-radius 0.2s ease;
}
.app-header--abierto {
  border-radius: 24px 24px 0 0;
}
.app-header__fila {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.6rem 0.9rem;
}
.app-header__marca {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}
.app-header__logo {
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--eca-green-900);
  border: 1.5px solid rgba(255, 255, 255, 0.65);
  color: var(--eca-green-200);
}
.app-header__logo svg {
  width: 1.05rem;
  height: 1.05rem;
}
.app-header__marca-texto {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.app-header__nombre {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--eca-green-200);
  text-transform: uppercase;
}
.app-header__usuario {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.75);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 46vw;
}
.app-header__acciones {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}
.app-header__conexion {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.7rem;
  padding: 0.25rem 0.55rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}
.app-header__conexion svg {
  width: 13px;
  height: 13px;
}
.app-header__conexion--offline {
  background: rgba(245, 196, 81, 0.25);
  color: var(--eca-gold);
}
.app-header__conexion-texto {
  display: none;
}
@media (min-width: 400px) {
  .app-header__conexion-texto {
    display: inline;
  }
}
.app-header__hamburguesa {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  cursor: pointer;
  transition: background 0.15s ease;
}
.app-header__hamburguesa:hover {
  background: rgba(255, 255, 255, 0.22);
}
.app-header__hamburguesa svg {
  width: 20px;
  height: 20px;
}

.app-menu {
  position: fixed;
  top: calc(56px + env(safe-area-inset-top, 0px));
  left: 8px;
  right: 8px;
  z-index: 30;
  background: var(--eca-green-900);
  border-radius: 0 0 24px 24px;
  box-shadow: var(--eca-shadow-card);
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.app-menu__enlace {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.65rem 0.75rem;
  border-radius: 12px;
  color: #fff;
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 500;
  border: none;
  background: transparent;
  cursor: pointer;
  width: 100%;
  text-align: left;
}
.app-menu__enlace svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
.app-menu__enlace:hover {
  background: rgba(255, 255, 255, 0.1);
}
.app-menu__enlace--activo {
  background: var(--eca-green-600);
}
.app-menu__separador {
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  margin: 0.3rem 0;
}
.app-menu__salir {
  color: #fecaca;
}
.app-menu__salir:hover {
  background: rgba(220, 38, 38, 0.18);
}

.app-menu__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  z-index: 20;
}

.menu-slide-enter-active,
.menu-slide-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.menu-slide-enter-from,
.menu-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
