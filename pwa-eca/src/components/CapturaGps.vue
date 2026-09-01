<!-- pwa-eca — captura de GPS con feedback visual (ECA-014).
     Se dispara sola al montarse; nunca bloquea: mientras no haya resultado,
     el formulario que la usa se puede guardar igual (estado_gps='SIN_GPS'). -->
<script setup>
import { ref, onMounted } from 'vue'
import { capturarGps } from '../services/gps'

const emit = defineEmits(['capturado'])

const capturando = ref(true)
const resultado = ref(null)

const ETIQUETAS = {
  CON_GPS: 'Ubicación buena',
  GPS_IMPRECISO: 'Ubicación imprecisa',
  SIN_GPS: 'Sin señal GPS',
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
    <span v-if="capturando">Buscando ubicación…</span>
    <template v-else>
      <span>{{ ETIQUETAS[resultado.estado_gps] }}</span>
      <span v-if="resultado.precision_gps_m"> (±{{ Math.round(resultado.precision_gps_m) }} m)</span>
      <button type="button" class="eca-btn eca-btn-secundario captura-gps__reintentar" @click="capturar">Reintentar</button>
    </template>
  </div>
</template>

<style scoped>
.captura-gps {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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
.captura-gps__reintentar {
  min-height: unset;
  padding: 0.3rem 0.7rem;
  font-size: 0.8rem;
}
</style>
