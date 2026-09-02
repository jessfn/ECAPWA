<!-- pwa-eca — botón de ubicación circular tipo Apple, compartido.
     Extraído de JornadaAccionModal.vue para reutilizarse EXACTAMENTE
     igual (mismo componente, no una copia) en cualquier flujo que pida
     GPS — pedido explícito: "actividades debe usar el mismo diseño de
     botón exactamente que entrada y salida". Calca `.apple-location-btn`
     de pwasuper (anillo de progreso, pulso de éxito, chips de lat/lon a
     6 decimales), con los mismos 4 estados ya usados en Jornada:
     cargando / lista (CON_GPS) / imprecisa (GPS_IMPRECISO) / sin-señal.
     Diferencia deliberada y confirmada con el usuario respecto a
     pwasuper: nunca se inventa una coordenada de respaldo — ver
     `services/gps.js`. -->
<script setup>
import { computed } from 'vue'
import AuthIcon from './auth/AuthIcon.vue'

const props = defineProps({
  capturando: { type: Boolean, default: false },
  gps: { type: Object, default: null },
  // Deshabilita el botón sin cambiar su apariencia (p. ej. mientras se
  // confirma/envía el formulario que lo contiene) — distinto de
  // `capturando`, que sí cambia el estado visual a "cargando".
  deshabilitado: { type: Boolean, default: false },
})
defineEmits(['reintentar'])

const estado = computed(() => {
  if (props.capturando) {
    return { clase: 'ubicacion-apple__boton--cargando', icono: 'map-pin', titulo: 'Obteniendo…', subtitulo: 'Espera un momento' }
  }
  const g = props.gps
  if (g?.estado_gps === 'CON_GPS') {
    return { clase: 'ubicacion-apple__boton--lista', icono: 'check', titulo: 'Ubicación lista', subtitulo: 'Coordenadas capturadas' }
  }
  if (g?.estado_gps === 'GPS_IMPRECISO') {
    return {
      clase: 'ubicacion-apple__boton--imprecisa',
      icono: 'map-pin',
      titulo: 'Ubicación aproximada',
      subtitulo: g.precision_gps_m ? `±${Math.round(g.precision_gps_m)} m de precisión` : 'Precisión limitada',
    }
  }
  return {
    clase: 'ubicacion-apple__boton--sin-senal',
    icono: 'alert',
    titulo: 'Sin ubicación',
    subtitulo: g?.permiso_denegado ? 'Permiso denegado' : 'Toca para reintentar',
  }
})
</script>

<template>
  <div class="ubicacion-apple">
    <div class="ubicacion-apple__envoltura">
      <button
        type="button"
        class="ubicacion-apple__boton"
        :class="estado.clase"
        :disabled="capturando || deshabilitado"
        :aria-label="capturando ? 'Obteniendo ubicación' : 'Obtener ubicación de nuevo'"
        @click="$emit('reintentar')"
      >
        <span v-if="capturando" class="ubicacion-apple__anillo">
          <svg class="ubicacion-apple__anillo-svg" viewBox="0 0 100 100">
            <circle class="ubicacion-apple__anillo-fondo" cx="50" cy="50" r="45" />
            <circle class="ubicacion-apple__anillo-progreso" cx="50" cy="50" r="45" />
          </svg>
        </span>
        <span v-if="gps?.estado_gps === 'CON_GPS' && !capturando" class="ubicacion-apple__pulso"></span>
        <span class="ubicacion-apple__icono">
          <AuthIcon :name="estado.icono" />
        </span>
      </button>

      <div class="ubicacion-apple__info">
        <span class="ubicacion-apple__titulo">{{ estado.titulo }}</span>
        <span class="ubicacion-apple__subtitulo">{{ estado.subtitulo }}</span>
      </div>
    </div>

    <div v-if="gps?.latitud != null" class="ubicacion-apple__coords" :class="{ 'ubicacion-apple__coords--aviso': gps.estado_gps === 'GPS_IMPRECISO' }">
      <span class="ubicacion-apple__coord"><b>Lat</b> {{ gps.latitud.toFixed(6) }}</span>
      <span class="ubicacion-apple__coord-sep"></span>
      <span class="ubicacion-apple__coord"><b>Lon</b> {{ gps.longitud.toFixed(6) }}</span>
    </div>

    <p v-if="gps?.permiso_denegado" class="ubicacion-apple__aviso-permiso">
      Activa el permiso de ubicación de este sitio en tu dispositivo y toca el círculo para reintentar.
    </p>
  </div>
</template>

<style scoped>
.ubicacion-apple {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
}
.ubicacion-apple__envoltura {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}
.ubicacion-apple__boton {
  position: relative;
  width: 4.5rem;
  height: 4.5rem;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
  -webkit-tap-highlight-color: transparent;
}
.ubicacion-apple__boton:disabled {
  cursor: default;
}
.ubicacion-apple__boton:not(:disabled):hover {
  transform: scale(1.05);
}
.ubicacion-apple__boton:not(:disabled):active {
  transform: scale(0.95);
}
.ubicacion-apple__icono {
  display: flex;
  color: #fff;
  z-index: 2;
}
.ubicacion-apple__icono svg {
  width: 1.8rem;
  height: 1.8rem;
}

.ubicacion-apple__boton--cargando {
  background: linear-gradient(180deg, #5ac8fa 0%, #34aadc 100%);
  box-shadow: 0 6px 18px rgba(90, 200, 250, 0.4);
  cursor: wait;
}
.ubicacion-apple__boton--lista {
  background: linear-gradient(180deg, #30d158 0%, #16a34a 100%);
  box-shadow: 0 6px 18px rgba(22, 163, 74, 0.4);
}
.ubicacion-apple__boton--imprecisa {
  background: linear-gradient(180deg, #fbbf24 0%, #d97706 100%);
  box-shadow: 0 6px 18px rgba(217, 119, 6, 0.35);
}
.ubicacion-apple__boton--sin-senal {
  background: linear-gradient(180deg, #9ca3af 0%, #6b7280 100%);
  box-shadow: 0 4px 14px rgba(107, 114, 128, 0.3);
}

.ubicacion-apple__anillo {
  position: absolute;
  inset: -5px;
  z-index: 1;
  animation: ubicacion-apple-girar 1s linear infinite;
}
.ubicacion-apple__anillo-svg {
  width: 100%;
  height: 100%;
}
.ubicacion-apple__anillo-fondo {
  fill: none;
  stroke: rgba(255, 255, 255, 0.2);
  stroke-width: 4;
}
.ubicacion-apple__anillo-progreso {
  fill: none;
  stroke: #fff;
  stroke-width: 4;
  stroke-linecap: round;
  stroke-dasharray: 70 213;
  transform-origin: center;
}
@keyframes ubicacion-apple-girar {
  to {
    transform: rotate(360deg);
  }
}

.ubicacion-apple__pulso {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(22, 163, 74, 0.3);
  animation: ubicacion-apple-pulso 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  z-index: 0;
}
@keyframes ubicacion-apple-pulso {
  0%, 100% {
    transform: scale(1);
    opacity: 0.6;
  }
  50% {
    transform: scale(1.2);
    opacity: 0;
  }
}

.ubicacion-apple__info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
}
.ubicacion-apple__titulo {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--eca-ink);
}
.ubicacion-apple__subtitulo {
  font-size: 0.75rem;
  color: var(--eca-ink-soft);
}

.ubicacion-apple__coords {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: var(--eca-green-100);
  border: 1px solid var(--eca-green-400);
  border-radius: 999px;
  padding: 0.3rem 0.75rem;
  font-size: 0.72rem;
  color: var(--eca-green-800);
  animation: ubicacion-apple-coords-entrar 0.3s ease both;
  max-width: 100%;
}
.ubicacion-apple__coords--aviso {
  background: var(--eca-warn-bg);
  border-color: var(--eca-warn);
  color: var(--eca-warn);
}
.ubicacion-apple__coord b {
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.62rem;
  margin-right: 0.2rem;
}
.ubicacion-apple__coord-sep {
  width: 1px;
  height: 0.7rem;
  background: currentColor;
  opacity: 0.35;
}
@keyframes ubicacion-apple-coords-entrar {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.ubicacion-apple__aviso-permiso {
  margin: -0.2rem 0 0;
  font-size: 0.78rem;
  color: var(--eca-ink-soft);
  text-align: center;
}
</style>
