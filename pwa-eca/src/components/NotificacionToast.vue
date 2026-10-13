<!-- pwa-eca — aviso emergente cuando llega una notificación con la app abierta.
     Baja desde arriba (bajo la zona segura), se cierra solo a los 6 s, se
     descarta deslizando hacia arriba y al tocarlo abre esa notificación. -->
<script setup>
import { computed, watch, onBeforeUnmount } from 'vue'
import { useNotificacionesStore } from '../stores/notificaciones'
import AuthIcon from './auth/AuthIcon.vue'

const store = useNotificacionesStore()
const COLORES = { INFO: '#2563eb', EXITO: '#16a34a', ALERTA: '#d97706', URGENTE: '#dc2626' }

// Solo se muestra una a la vez (la más reciente de la cola).
const actual = computed(() => store.toasts[store.toasts.length - 1] || null)

let temporizador = null
watch(
  actual,
  (t) => {
    clearTimeout(temporizador)
    if (t) temporizador = setTimeout(() => store.cerrarToast(t.uuid), 6000)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearTimeout(temporizador))

let inicioY = null
function alTocar(e) {
  inicioY = e.touches[0].clientY
}
function alSoltar(e) {
  if (inicioY !== null && inicioY - e.changedTouches[0].clientY > 24 && actual.value) store.cerrarToast(actual.value.uuid)
  inicioY = null
}
function abrir() {
  if (actual.value) store.abrirPanel(actual.value.uuid)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="nt">
      <button
        v-if="actual"
        :key="actual.uuid"
        type="button"
        class="nt"
        :style="{ '--c': COLORES[actual.tipo] }"
        @click="abrir"
        @touchstart.passive="alTocar"
        @touchend.passive="alSoltar"
      >
        <span class="nt__icono"><AuthIcon name="bell" /></span>
        <span class="nt__texto">
          <small>Nueva notificación</small>
          <strong>{{ actual.titulo }}</strong>
          <em v-if="actual.subtitulo">{{ actual.subtitulo }}</em>
        </span>
        <span class="nt__progreso"></span>
      </button>
    </Transition>
  </Teleport>
</template>

<style scoped>
.nt {
  position: fixed; z-index: 90; left: 12px; right: 12px; max-width: 460px; margin: 0 auto;
  top: max(10px, calc(env(safe-area-inset-top, 0px) + 6px));
  display: flex; align-items: center; gap: 0.75rem; padding: 0.8rem 0.9rem; text-align: left; font-family: inherit;
  border: 1px solid rgba(255, 255, 255, 0.7); border-radius: 22px; cursor: pointer; overflow: hidden;
  background: rgba(255, 255, 255, 0.82); backdrop-filter: blur(18px) saturate(1.6);
  box-shadow: 0 18px 44px rgba(2, 20, 10, 0.28), 0 2px 8px rgba(2, 20, 10, 0.1);
}
.nt__icono { flex-shrink: 0; width: 2.6rem; height: 2.6rem; border-radius: 15px; display: flex; align-items: center; justify-content: center; color: #fff; background: linear-gradient(135deg, var(--c), color-mix(in srgb, var(--c) 65%, #000)); box-shadow: 0 6px 16px color-mix(in srgb, var(--c) 45%, transparent); animation: nt-sacude 0.7s ease 0.35s; transform-origin: 50% 0; }
.nt__icono svg { width: 1.2rem; height: 1.2rem; }
.nt__texto { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.08rem; }
.nt__texto small { font-size: 0.64rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: var(--c); }
.nt__texto strong { font-size: 0.92rem; line-height: 1.25; color: var(--eca-ink); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.nt__texto em { font-style: normal; font-size: 0.78rem; color: var(--eca-ink-soft); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nt__progreso { position: absolute; left: 0; bottom: 0; height: 3px; background: var(--c); animation: nt-barra 6s linear forwards; }
@keyframes nt-barra { from { width: 100%; } to { width: 0; } }
@keyframes nt-sacude { 0%, 100% { transform: rotate(0); } 20% { transform: rotate(-14deg); } 40% { transform: rotate(12deg); } 60% { transform: rotate(-8deg); } 80% { transform: rotate(5deg); } }

.nt-enter-active { transition: transform 0.5s cubic-bezier(0.34, 1.45, 0.64, 1), opacity 0.3s ease; }
.nt-leave-active { transition: transform 0.28s ease, opacity 0.25s ease; }
.nt-enter-from, .nt-leave-to { opacity: 0; transform: translateY(-120%) scale(0.96); }
@media (prefers-reduced-motion: reduce) { .nt__icono, .nt__progreso { animation: none; } }
</style>
