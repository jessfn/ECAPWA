<!-- pwa-eca — selector de ECA (ECA-013 + ECA-018).
     Las ECA "propias" del técnico (REGLA DE ECA) vienen de IndexedDB
     (pobladas por `bootstrap`/`pull`) — funciona 100 % offline. Buscar por
     nombre: si hay red, amplía con `GET /ecas?q=` paginado server-side
     (nunca las ~5 000 filas completas); sin red, filtra la lista local. -->
<script setup>
import { ref, onMounted, watch } from 'vue'
import { api } from '../services/api'
import { useEcasStore } from '../stores/ecas'
import { useConectividad } from '../services/conectividad'

const props = defineProps({ modelValue: { type: Number, default: null } })
const emit = defineEmits(['update:modelValue'])

const ecas = useEcasStore()
const { enLinea } = useConectividad()

const resultadosBusqueda = ref([])
const buscando = ref(false)
const q = ref('')
let temporizador = null

async function buscar() {
  if (!q.value.trim()) {
    resultadosBusqueda.value = []
    return
  }
  if (!enLinea.value) {
    resultadosBusqueda.value = ecas.buscar(q.value).map((e) => ({ id: e.eca_id, uuid: e.eca_id, nombre: e.eca_nombre }))
    return
  }
  buscando.value = true
  try {
    const { data } = await api.get('/ecas', { params: { q: q.value, page: 1, page_size: 20 } })
    resultadosBusqueda.value = data.resultados
  } catch {
    resultadosBusqueda.value = ecas.buscar(q.value).map((e) => ({ id: e.eca_id, uuid: e.eca_id, nombre: e.eca_nombre }))
  } finally {
    buscando.value = false
  }
}

watch(q, () => {
  clearTimeout(temporizador)
  temporizador = setTimeout(buscar, 300)
})

function seleccionar(ecaId) {
  emit('update:modelValue', ecaId)
}

onMounted(() => ecas.cargar())
</script>

<template>
  <div class="selector-eca">
    <input v-model="q" type="text" class="eca-input" placeholder="Buscar ECA por nombre…" />

    <template v-if="!q.trim()">
      <p v-if="!ecas.items.length" class="eca-ayuda">
        No tienes ECA asignadas ni en tu ámbito. Busca por nombre arriba.
      </p>
      <ul v-else class="selector-eca__lista">
        <li v-for="e in ecas.items" :key="e.eca_id">
          <label>
            <input
              type="radio"
              name="eca"
              :checked="modelValue === e.eca_id"
              @change="seleccionar(e.eca_id)"
            />
            {{ e.eca_nombre }}
            <small v-if="e.origen === 'ASIGNACION_DIRECTA'">(asignada)</small>
          </label>
        </li>
      </ul>
    </template>

    <template v-else>
      <p v-if="buscando">Buscando…</p>
      <ul v-else class="selector-eca__lista">
        <li v-for="e in resultadosBusqueda" :key="e.uuid">
          <label>
            <input
              type="radio"
              name="eca"
              :checked="modelValue === e.id"
              @change="seleccionar(e.id)"
            />
            {{ e.nombre }}
          </label>
        </li>
        <li v-if="!resultadosBusqueda.length">Sin resultados.</li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.selector-eca__lista {
  list-style: none;
  padding: 0;
  margin: 0.6rem 0 0;
  max-height: 30vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.selector-eca__lista li {
  padding: 0.4rem 0.6rem;
  border-radius: var(--eca-r-sm);
  background: var(--eca-surface);
}
</style>
