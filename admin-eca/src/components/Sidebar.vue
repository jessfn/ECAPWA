<!-- admin-eca — sidebar del panel autenticado. Mismo lenguaje visual que el
     sidebar de `admin-pwa` (gradiente verde, tarjeta de usuario "liquid
     glass", animaciones de navegación, modal de cerrar sesión): pedido
     explícito de paridad de diseño con "seguimiento SADER". Se omiten las
     secciones específicas de ese dominio (territorios, Geoportal/App Móvil)
     porque no aplican a ECA; la navegación es la propia de este panel. -->
<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AuthIcon from './auth/AuthIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const showLogoutModal = ref(false)

const enlaces = [
  { nombre: 'inicio', etiqueta: 'Inicio', ruta: { name: 'inicio' }, permiso: null, icono: 'home' },
  { nombre: 'geografia', etiqueta: 'Geografía', ruta: { name: 'geografia' }, permiso: null, icono: 'map' },
  { nombre: 'ecas', etiqueta: 'ECA', ruta: { name: 'ecas' }, permiso: 'ecas.ver', icono: 'school' },
  { nombre: 'ambitos', etiqueta: 'Ámbitos', ruta: { name: 'ambitos' }, permiso: 'ambitos.gestionar', icono: 'shield' },
  {
    nombre: 'asignaciones',
    etiqueta: 'Asignaciones',
    ruta: { name: 'asignaciones' },
    permiso: 'asignaciones.gestionar',
    icono: 'check-circle',
  },
  { nombre: 'catalogos', etiqueta: 'Catálogos', ruta: { name: 'catalogos' }, permiso: null, icono: 'book' },
  {
    nombre: 'tecnicos',
    etiqueta: 'Técnicos',
    ruta: { name: 'tecnicos' },
    permiso: 'usuarios.gestionar',
    icono: 'user',
  },
  {
    nombre: 'actividades',
    etiqueta: 'Actividades',
    ruta: { name: 'actividades' },
    permiso: 'actividades.ver_todas',
    icono: 'clock',
  },
  {
    nombre: 'solicitudes-acceso',
    etiqueta: 'Solicitudes de acceso',
    ruta: { name: 'solicitudes-acceso' },
    permiso: 'usuarios.gestionar',
    icono: 'user-plus',
  },
]

const enlacesVisibles = computed(() => enlaces.filter((e) => !e.permiso || auth.tienePermiso(e.permiso)))

function iniciales(nombre, apellido) {
  const n = (nombre || '').trim()
  const a = (apellido || '').trim()
  if (n && a) return (n[0] + a[0]).toUpperCase()
  return n ? n.slice(0, 2).toUpperCase() : 'AD'
}

function nombreCompleto() {
  const u = auth.usuario
  if (!u) return 'Usuario'
  return [u.nombre, u.apellido_paterno].filter(Boolean).join(' ')
}

function rolPrincipal() {
  return auth.permisos && auth.usuario?.roles?.length ? auth.usuario.roles[0] : null
}

function closeModal() {
  showLogoutModal.value = false
}

async function confirmLogout() {
  showLogoutModal.value = false
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo-container">
        <div class="brand-logo">
          <img src="/logo.png" alt="" />
        </div>
        <h1 class="brand-name">ECA</h1>
        <p class="brand-tagline">Escuelas de Campo</p>

        <div class="user-card">
          <span class="user-card-blob blob-a" aria-hidden="true"></span>
          <span class="user-card-blob blob-b" aria-hidden="true"></span>

          <div class="user-card-row">
            <div class="user-avatar">
              <span class="avatar-initials">{{ iniciales(auth.usuario?.nombre, auth.usuario?.apellido_paterno) }}</span>
              <div class="avatar-status"></div>
            </div>
            <div class="user-main-info">
              <h4 class="user-name-title">{{ nombreCompleto() }}</h4>
              <span class="user-handle">{{ auth.usuario?.correo }}</span>
            </div>
          </div>

          <span v-if="rolPrincipal()" class="user-role-badge">{{ rolPrincipal() }}</span>
        </div>

        <div class="text-underline"></div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <ul>
        <li
          v-for="enlace in enlacesVisibles"
          :key="enlace.nombre"
          class="nav-item"
          :class="{ active: route.name === enlace.ruta.name }"
        >
          <RouterLink :to="enlace.ruta" class="nav-link">
            <div class="nav-icon-container">
              <AuthIcon :name="enlace.icono" class="nav-icon" />
            </div>
            <span class="nav-text">{{ enlace.etiqueta }}</span>
          </RouterLink>
          <div class="nav-indicator"></div>
        </li>
      </ul>
    </nav>

    <div class="sidebar-footer">
      <button type="button" class="logout-button" @click="showLogoutModal = true">
        <AuthIcon name="logout" class="logout-icon" />
        <span>Cerrar sesión</span>
      </button>
    </div>

    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showLogoutModal" class="logout-modal-overlay" @click="closeModal">
          <div class="logout-modal-container" @click.stop>
            <div class="logout-modal-header">
              <div class="logout-header-content">
                <div class="logout-icon-container">
                  <div class="logout-icon-bg">
                    <AuthIcon name="logout" class="logout-icon" />
                  </div>
                </div>
                <div class="logout-header-text">
                  <h3 class="logout-title">Cerrar sesión</h3>
                  <p class="logout-subtitle">Finalizar tu sesión actual</p>
                </div>
              </div>
              <button type="button" class="logout-close-btn" @click="closeModal">
                <AuthIcon name="close" />
              </button>
            </div>

            <div class="logout-modal-body">
              <div class="logout-warning-section">
                <div class="logout-warning-icon">
                  <AuthIcon name="alert" />
                </div>
                <div class="logout-warning-content">
                  <h4 class="logout-warning-title">¿Confirmar cierre de sesión?</h4>
                  <p class="logout-warning-text">
                    Se cerrará tu sesión actual y tendrás que iniciar sesión nuevamente para acceder al sistema.
                  </p>
                </div>
              </div>
            </div>

            <div class="logout-modal-footer">
              <button type="button" class="logout-btn logout-btn-cancel" @click="closeModal">
                <span>Cancelar</span>
              </button>
              <button type="button" class="logout-btn logout-btn-confirm" @click="confirmLogout">
                <AuthIcon name="logout" class="logout-btn-icon" />
                <span>Cerrar sesión</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </aside>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Montserrat:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&family=Quicksand:wght@400;500;600;700&display=swap');

.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: min(220px, 18vw);
  max-width: 240px;
  min-width: 200px;
  background: linear-gradient(135deg, #388e3c 0%, #2e7d32 50%, #1b5e20 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  z-index: 1000;
  box-shadow: 4px 0 10px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
  overflow-x: hidden;
  font-family: 'Poppins', 'Segoe UI', sans-serif;
}

.sidebar-header {
  padding: 4px 12px 8px;
  position: relative;
}
.logo-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.brand-logo {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}
.brand-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.brand-name {
  font-family: 'Montserrat', sans-serif;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.5px;
  margin: 0;
  text-transform: uppercase;
  background: linear-gradient(135deg, #e8ffd4 0%, #d4ff9a 15%, #c6f76c 30%, #fff8b8 50%, #ffe566 70%, #ffdd44 85%, #ffd700 100%);
  background-size: 200% 200%;
  -webkit-background-clip: text;
  color: transparent;
  background-clip: text;
  animation: gradientTextBright 4s ease infinite;
}
@keyframes gradientTextBright {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.brand-tagline {
  font-size: 11px;
  font-weight: 500;
  color: #fff;
  opacity: 0.95;
  margin: 4px 0 0;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
.text-underline {
  width: 85%;
  height: 3px;
  background: linear-gradient(90deg, transparent 0%, #10b981 15%, #22c55e 35%, #4ade80 50%, #22c55e 65%, #10b981 85%, transparent 100%);
  margin: 8px auto 0 auto;
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.6), 0 0 15px rgba(34, 197, 94, 0.4), 0 0 25px rgba(74, 222, 128, 0.2);
}

.user-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 13px 16px 12px;
  margin: 12px auto 0;
  width: calc(100% - 12px);
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(14px) saturate(1.4);
  -webkit-backdrop-filter: blur(14px) saturate(1.4);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow:
    0 1px 0 0 rgba(255, 255, 255, 0.35) inset,
    0 -3px 8px 0 rgba(0, 0, 0, 0.18) inset,
    0 10px 26px rgba(0, 0, 0, 0.38),
    0 3px 8px rgba(0, 0, 0, 0.22),
    0 0 0 1px rgba(74, 222, 128, 0.12);
  position: relative;
  overflow: hidden;
}
.user-card-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(18px);
  pointer-events: none;
  z-index: 0;
}
.blob-a {
  width: 70px;
  height: 70px;
  top: -20px;
  left: -16px;
  background: radial-gradient(circle, rgba(74, 222, 128, 0.55) 0%, transparent 72%);
  animation: userCardDrift1 7s ease-in-out infinite;
}
.blob-b {
  width: 60px;
  height: 60px;
  bottom: -18px;
  right: -14px;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.5) 0%, transparent 72%);
  animation: userCardDrift2 9s ease-in-out infinite;
}
@keyframes userCardDrift1 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.7; }
  50% { transform: translate(10px, 12px) scale(1.25); opacity: 1; }
}
@keyframes userCardDrift2 {
  0%, 100% { transform: translate(0, 0) scale(1); opacity: 0.6; }
  50% { transform: translate(-8px, -10px) scale(1.2); opacity: 0.95; }
}
.user-card-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  z-index: 1;
}
.user-avatar {
  position: relative;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(145deg, #4ade80 0%, #22c55e 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(74, 222, 128, 0.45), 0 0 0 2px rgba(5, 46, 22, 1), 0 0 0 4px rgba(74, 222, 128, 0.25);
  flex-shrink: 0;
  z-index: 1;
}
.avatar-initials {
  font-size: 13px;
  font-weight: 700;
  color: white;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  letter-spacing: 0.5px;
  font-family: 'Quicksand', sans-serif;
}
.avatar-status {
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 10px;
  height: 10px;
  background: linear-gradient(135deg, #86efac 0%, #4ade80 100%);
  border-radius: 50%;
  border: 2px solid #052e16;
  box-shadow: 0 0 8px rgba(134, 239, 172, 0.7);
  animation: pulse-glow 2s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 8px rgba(134, 239, 172, 0.7); transform: scale(1); }
  50% { box-shadow: 0 0 14px rgba(134, 239, 172, 0.9); transform: scale(1.05); }
}
.user-main-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.user-name-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 700;
  color: #dcfce7;
  letter-spacing: 0.2px;
  line-height: 1.3;
  font-family: 'Quicksand', sans-serif;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.user-handle {
  font-size: 10px;
  color: #bbf7d0;
  font-weight: 500;
  font-family: 'Quicksand', sans-serif;
  opacity: 0.85;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.user-role-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  font-size: 7px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: #86efac;
  background: linear-gradient(135deg, rgba(134, 239, 172, 0.15) 0%, rgba(74, 222, 128, 0.22) 100%);
  border: 1px solid rgba(134, 239, 172, 0.4);
  border-radius: 20px;
  font-family: 'Quicksand', sans-serif;
  z-index: 1;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px 12px;
}
.sidebar-nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.nav-item {
  position: relative;
  margin-bottom: 5px;
  overflow: hidden;
}
.nav-link {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  text-decoration: none;
  color: #fff;
  border-radius: 15px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  font-weight: 400;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
.nav-link::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0);
  transition: all 0.5s ease;
  border-radius: 15px;
  transform: scale(0.95);
  opacity: 0;
}
.nav-link:hover::before {
  background: rgba(255, 255, 255, 0.15);
  transform: scale(1);
  opacity: 1;
}
.nav-icon-container {
  width: 26px;
  height: 26px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
  position: relative;
  z-index: 1;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.nav-icon {
  width: 14px;
  height: 14px;
  color: #fff;
}
.nav-text {
  font-size: 12px;
  font-weight: 400;
  position: relative;
  z-index: 1;
  letter-spacing: 0.3px;
  color: #fff;
}
.nav-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 4px;
  height: 70%;
  background: #fff8d;
  border-radius: 0 4px 4px 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0;
  box-shadow: 0 0 10px rgba(255, 255, 141, 0.6);
}
.nav-item.active .nav-link::before {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0.1) 50%, rgba(255, 255, 255, 0.3) 100%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  transform: scale(1);
  opacity: 1;
}
.nav-item.active .nav-icon-container {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.5) 0%, rgba(255, 255, 255, 0.2) 50%, rgba(255, 255, 255, 0.4) 100%);
  border: 1px solid rgba(255, 255, 255, 0.4);
  transform: translateY(-1px) scale(1.05);
}
.nav-item.active .nav-indicator {
  opacity: 1;
  transform: translateY(-50%) scaleY(1);
}

.sidebar-footer {
  padding: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.logout-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(255, 87, 34, 0.9) 0%, rgba(244, 67, 54, 0.9) 100%);
  color: white;
  font-family: 'Poppins', sans-serif;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
  width: 100%;
}
.logout-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
}
.logout-icon {
  width: 15px;
  height: 15px;
}

.logout-modal-overlay {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.4) 0%, rgba(20, 20, 20, 0.6) 50%, rgba(0, 0, 0, 0.8) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(12px);
  padding: 20px;
}
.logout-modal-container {
  width: 100%;
  max-width: 340px;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.4);
}
.logout-modal-header {
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 25%, #f87171 50%, #ef4444 75%, #dc2626 100%);
  background-size: 300% 300%;
  animation: gradientShift 6s ease infinite;
  padding: 18px;
  position: relative;
}
@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
.logout-header-content {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  z-index: 2;
}
.logout-icon-bg {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.25) 0%, rgba(255, 255, 255, 0.1) 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.2);
}
.logout-icon-bg .logout-icon {
  width: 24px;
  height: 24px;
  color: #fff;
}
.logout-header-text { flex: 1; }
.logout-title {
  margin: 0 0 3px 0;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  font-family: 'Inter', sans-serif;
}
.logout-subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}
.logout-close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #fff;
  z-index: 3;
}
.logout-close-btn:hover { transform: rotate(90deg) scale(1.1); }
.logout-modal-body { padding: 24px 18px; background: #fff; }
.logout-warning-section {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border-radius: 10px;
  border: 1px solid #fecaca;
  position: relative;
}
.logout-warning-section::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(to bottom, #dc2626, #ef4444);
}
.logout-warning-icon {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.logout-warning-content { flex: 1; }
.logout-warning-title {
  margin: 0 0 6px 0;
  font-size: 15px;
  font-weight: 600;
  color: #7f1d1d;
  font-family: 'Inter', sans-serif;
}
.logout-warning-text {
  margin: 0;
  font-size: 13px;
  color: #991b1b;
  line-height: 1.4;
}
.logout-modal-footer {
  padding: 16px 18px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.logout-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 8px;
  border: none;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}
.logout-btn-cancel {
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #475569;
  border: 2px solid #cbd5e1;
}
.logout-btn-cancel:hover { transform: translateY(-1px); }
.logout-btn-confirm {
  background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
  color: #fff;
  border: 2px solid #dc2626;
}
.logout-btn-confirm:hover { transform: translateY(-2px); }

.modal-enter-active { transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.modal-enter-from { opacity: 0; transform: scale(0.8) translateY(20px); }
.modal-leave-to { opacity: 0; transform: scale(0.95) translateY(-10px); }
</style>
