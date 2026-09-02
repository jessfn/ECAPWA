<!-- pwa-eca — captura de GPS para actividades (ECA-014 + ECA-021).
     Se dispara sola al montarse; nunca bloquea: mientras no haya
     resultado, el formulario que la usa se puede guardar igual
     (estado_gps='SIN_GPS'). Usa el MISMO botón circular tipo Apple que
     ya se usa en Jornada — pedido explícito: "actividades debe usar el
     mismo diseño de botón exactamente que entrada y salida" — así que
     esto es un envoltorio delgado sobre `UbicacionApple.vue`, no una
     copia con su propio diseño. -->
<script setup>
import { ref, onMounted } from 'vue'
import { capturarGps } from '../services/gps'
import UbicacionApple from './UbicacionApple.vue'

const emit = defineEmits(['capturado'])

const capturando = ref(true)
const resultado = ref(null)

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
  <UbicacionApple :capturando="capturando" :gps="resultado" @reintentar="capturar" />
</template>
