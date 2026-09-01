<!-- pwa-eca — captura de evidencias fotográficas (ECA-015).
     1–3 fotos (cámara o galería), previsualización, compresión antes de
     guardar. El mínimo exigido (`min_fotos`) lo indica el tipo de
     actividad seleccionado — se muestra como ayuda, la subida real ocurre
     después de guardar la actividad (`NuevaActividadView`). -->
<script setup>
import { ref, computed } from 'vue'
import { comprimirImagen, blobAArchivo } from '../services/imagen'

const props = defineProps({
  minFotos: { type: Number, default: 0 },
  maxFotos: { type: Number, default: 3 },
})
const emit = defineEmits(['update:fotos'])

const fotos = ref([]) // [{ id, archivo, previsualizacion }]
const comprimiendo = ref(false)
const error = ref('')

const puedeAgregarMas = computed(() => fotos.value.length < props.maxFotos)

async function onSeleccionArchivos(evento) {
  error.value = ''
  const seleccionados = Array.from(evento.target.files || [])
  evento.target.value = ''

  const espacio = props.maxFotos - fotos.value.length
  const aProcesar = seleccionados.slice(0, espacio)
  if (seleccionados.length > espacio) {
    error.value = `Solo se permiten ${props.maxFotos} fotos por actividad.`
  }

  comprimiendo.value = true
  try {
    for (const original of aProcesar) {
      const comprimido = blobAArchivo(await comprimirImagen(original), original.name.replace(/\.\w+$/, '.jpg'))
      fotos.value.push({
        id: crypto.randomUUID(),
        archivo: comprimido,
        previsualizacion: URL.createObjectURL(comprimido),
      })
    }
  } catch {
    error.value = 'No se pudo procesar una de las fotos.'
  } finally {
    comprimiendo.value = false
    emit('update:fotos', fotos.value)
  }
}

function quitar(id) {
  const foto = fotos.value.find((f) => f.id === id)
  if (foto) URL.revokeObjectURL(foto.previsualizacion)
  fotos.value = fotos.value.filter((f) => f.id !== id)
  emit('update:fotos', fotos.value)
}
</script>

<template>
  <div class="captura-evidencia">
    <p class="captura-evidencia__ayuda eca-ayuda">
      {{ fotos.length }}/{{ maxFotos }} fotos
      <template v-if="minFotos">(mínimo {{ minFotos }})</template>
    </p>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

    <ul class="captura-evidencia__lista">
      <li v-for="f in fotos" :key="f.id">
        <img :src="f.previsualizacion" alt="Evidencia" />
        <button type="button" class="eca-btn eca-btn-peligro captura-evidencia__quitar" @click="quitar(f.id)">Quitar</button>
      </li>
    </ul>

    <label v-if="puedeAgregarMas" class="captura-evidencia__agregar">
      {{ comprimiendo ? 'Procesando…' : '+ Agregar foto' }}
      <input
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        :disabled="comprimiendo"
        @change="onSeleccionArchivos"
      />
    </label>
  </div>
</template>

<style scoped>
.captura-evidencia__lista {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}
.captura-evidencia__lista li {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
}
.captura-evidencia__lista img {
  width: 90px;
  height: 90px;
  object-fit: cover;
  border-radius: var(--eca-r-sm);
  box-shadow: var(--eca-shadow-card);
}
.captura-evidencia__quitar {
  min-height: unset;
  padding: 0.25rem 0.6rem;
  font-size: 0.75rem;
}
.captura-evidencia__agregar {
  display: inline-block;
  padding: 0.6rem 0.9rem;
  border: 2px dashed var(--eca-green-300);
  border-radius: var(--eca-r-sm);
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--eca-green-700);
  font-weight: 600;
}
.captura-evidencia__agregar input {
  display: none;
}
</style>
