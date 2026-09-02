<!-- pwa-eca — captura de GPS con feedback visual (ECA-014).
     Se dispara sola al montarse; nunca bloquea: mientras no haya resultado,
     el formulario que la usa se puede guardar igual (estado_gps='SIN_GPS').
     Botón circular con icono de ubicación (pedido explícito) — clicable en
     todo momento, no solo tras fallar, para volver a pedir la ubicación
     exacta cuando el usuario quiera (p. ej. si se movió de lugar). -->
<script setup>
import { ref, onMounted } from 'vue'
import { capturarGps } from '../services/gps'
import AuthIcon from './auth/AuthIcon.vue'

const emit = defineEmits(['capturado'])

const capturando = ref(true)
const resultado = ref(null)

const ETIQUETAS = {
  CON_GPS: 'Ubicación exacta obtenida',
  GPS_IMPRECISO: 'Ubicación aproximada',
  SIN_GPS: 'Sin señal de ubicación',
}

async function capturar() {
  capturando.value = true
  resultado.value = await capturarGps()
  capturando.value = false
  emit('capturado', resultado.value)
}

onMounted(capturar)

defineExpose({ recapturar: capturar })
</script>

<template>
  <div class="captura-gps" :class="`captura-gps--${resultado?.estado_gps?.toLowerCase() || 'buscando'}`">
    <button
      type="button"
      class="captura-gps__boton"
      :disabled="capturando"
      :aria-label="capturando ? 'Obteniendo ubicación' : 'Obtener ubicación'"
      @click="capturar"
    >
      <span v-if="capturando" class="captura-gps__spin"></span>
      <AuthIcon v-else name="map-pin" />
    </button>

    <span class="captura-gps__texto">
      <strong v-if="capturando">Obteniendo tu ubicación…</strong>
      <template v-else>
        <strong>{{ ETIQUETAS[resultado.estado_gps] }}</strong>
        <span v-if="resultado.precision_gps_m" class="captura-gps__precision">
          ±{{ Math.round(resultado.precision_gps_m) }} m
        </span>
        <span v-if="resultado.permiso_denegado" class="captura-gps__aviso">
          Activa el permiso de ubicación de este sitio en tu dispositivo y toca el botón para reintentar.
        </span>
      </template>
    </span>
  </div>
</template>

<style scoped>
.captura-gps {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.85rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--eca-r-sm);
  background: var(--eca-surface);
}
.captura-gps--con_gps {
  background: var(--eca-green-100);
  color: var(--eca-green-800);
}
.captura-gps--gps_impreciso {
  background: var(--eca-warn-bg);
  color: var(--eca-warn);
}
.captura-gps--sin_gps {
  background: var(--eca-danger-bg);
  color: var(--eca-danger);
}

/* Botón circular de "obtener ubicación" — pedido explícito. */
.captura-gps__boton {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--eca-green-600);
  color: #fff;
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease;
}
.captura-gps__boton:hover:not(:disabled) {
  background: var(--eca-green-700);
  transform: scale(1.05);
}
.captura-gps__boton:active:not(:disabled) {
  transform: scale(0.95);
}
.captura-gps__boton:disabled {
  cursor: default;
  opacity: 0.85;
}
.captura-gps--gps_impreciso .captura-gps__boton {
  background: var(--eca-warn);
}
.captura-gps--sin_gps .captura-gps__boton {
  background: var(--eca-danger);
}
.captura-gps__boton svg {
  width: 1.15rem;
  height: 1.15rem;
}
.captura-gps__spin {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: captura-gps-spin 0.7s linear infinite;
}
@keyframes captura-gps-spin {
  to {
    transform: rotate(360deg);
  }
}

.captura-gps__texto {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.captura-gps__precision {
  opacity: 0.85;
  font-weight: 400;
}
.captura-gps__aviso {
  font-weight: 400;
  font-size: 0.78rem;
}

@media (prefers-reduced-motion: reduce) {
  .captura-gps__spin {
    animation: none;
  }
}
</style>
