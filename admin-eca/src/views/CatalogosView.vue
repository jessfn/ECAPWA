<!-- admin-eca — pantalla "Catálogos" (ECA-010): activar/desactivar y editar
     modalidades, tipos de actividad, temas, subtemas y sistemas productivos.
     Lectura para cualquier autenticado; edición gateada por permiso en el
     backend (`catalogos.gestionar`) — aquí solo se oculta la UI de edición. -->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { listarCatalogo, editarItemCatalogo, crearSubtema } from '../services/catalogosService'

const auth = useAuthStore()
const puedeGestionar = computed(() => auth.tienePermiso('catalogos.gestionar'))

const TIPOS = [
  { valor: 'modalidades', etiqueta: 'Modalidades' },
  { valor: 'tipos-actividad', etiqueta: 'Tipos de actividad' },
  { valor: 'temas', etiqueta: 'Temas' },
  { valor: 'subtemas', etiqueta: 'Subtemas' },
  { valor: 'sistemas-productivos', etiqueta: 'Sistemas productivos' },
]

const tipoActivo = ref('modalidades')
const items = ref([])
const temas = ref([])
const cargando = ref(false)
const error = ref('')
const mensaje = ref('')

const nuevoSubtemaTemaId = ref(null)
const nuevoSubtemaClave = ref('')
const nuevoSubtemaNombre = ref('')
const creandoSubtema = ref(false)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    items.value = await listarCatalogo(tipoActivo.value, { todos: true })
    if (tipoActivo.value === 'subtemas' && !temas.value.length) {
      temas.value = await listarCatalogo('temas', { todos: true })
    }
  } catch {
    error.value = 'No se pudo cargar el catálogo.'
  } finally {
    cargando.value = false
  }
}

function nombreTema(temaId) {
  return temas.value.find((t) => t.id === temaId)?.nombre || `#${temaId}`
}

async function alternarActivo(item) {
  mensaje.value = ''
  error.value = ''
  try {
    const actualizado = await editarItemCatalogo(tipoActivo.value, item.id, { activo: !item.activo })
    item.activo = actualizado.activo
    mensaje.value = 'Actualizado.'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo actualizar.'
  }
}

async function guardarCampo(item, campo, valor) {
  mensaje.value = ''
  error.value = ''
  try {
    const actualizado = await editarItemCatalogo(tipoActivo.value, item.id, { [campo]: valor })
    Object.assign(item, actualizado)
    mensaje.value = 'Actualizado.'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo actualizar.'
  }
}

async function onCrearSubtema() {
  if (!nuevoSubtemaTemaId.value || !nuevoSubtemaClave.value || !nuevoSubtemaNombre.value) return
  creandoSubtema.value = true
  error.value = ''
  mensaje.value = ''
  try {
    await crearSubtema({
      temaId: nuevoSubtemaTemaId.value,
      clave: nuevoSubtemaClave.value,
      nombre: nuevoSubtemaNombre.value,
    })
    nuevoSubtemaClave.value = ''
    nuevoSubtemaNombre.value = ''
    mensaje.value = 'Subtema creado.'
    await cargar()
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo crear el subtema.'
  } finally {
    creandoSubtema.value = false
  }
}

watch(tipoActivo, cargar)
onMounted(cargar)
</script>

<template>
  <section class="eca-card catalogos">
    <h1 class="eca-titulo">Catálogos de actividad</h1>
    <p class="eca-ayuda catalogos__ayuda">
      Modalidades, tipos de actividad, temas, subtemas y sistemas productivos que usa la PWA de
      técnico. Los cambios aplican de inmediato, sin desplegar código.
    </p>

    <nav class="catalogos__tabs">
      <button
        v-for="t in TIPOS"
        :key="t.valor"
        type="button"
        class="eca-btn eca-btn-secundario catalogos__tab"
        :class="{ 'catalogos__tab--activo': tipoActivo === t.valor }"
        @click="tipoActivo = t.valor"
      >
        {{ t.etiqueta }}
      </button>
    </nav>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>
    <p v-if="mensaje" class="eca-alerta-ok">{{ mensaje }}</p>
    <p v-if="cargando" class="eca-ayuda">Cargando…</p>

    <table v-else class="eca-tabla catalogos__tabla">
      <thead>
        <tr>
          <th>Clave</th>
          <th>Nombre</th>
          <th v-if="tipoActivo === 'subtemas'">Tema</th>
          <th v-if="tipoActivo === 'tipos-actividad'">Evidencia</th>
          <th v-if="tipoActivo === 'tipos-actividad'">Fotos (min–max)</th>
          <th v-if="tipoActivo === 'tipos-actividad'">Participantes</th>
          <th v-if="tipoActivo === 'tipos-actividad'">Requiere ECA</th>
          <th>Activo</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>{{ item.clave }}</td>
          <td>{{ item.nombre }}</td>
          <td v-if="tipoActivo === 'subtemas'">{{ nombreTema(item.tema_id) }}</td>
          <template v-if="tipoActivo === 'tipos-actividad'">
            <td>
              <input
                type="checkbox"
                :checked="item.requiere_evidencia"
                :disabled="!puedeGestionar"
                @change="guardarCampo(item, 'requiere_evidencia', !item.requiere_evidencia)"
              />
            </td>
            <td>{{ item.min_fotos }}–{{ item.max_fotos }}</td>
            <td>
              <input
                type="checkbox"
                :checked="item.permite_participantes"
                :disabled="!puedeGestionar"
                @change="guardarCampo(item, 'permite_participantes', !item.permite_participantes)"
              />
            </td>
            <td>
              <input
                type="checkbox"
                :checked="item.requiere_eca"
                :disabled="!puedeGestionar"
                @change="guardarCampo(item, 'requiere_eca', !item.requiere_eca)"
              />
            </td>
          </template>
          <td>
            <input
              type="checkbox"
              :checked="item.activo"
              :disabled="!puedeGestionar"
              @change="alternarActivo(item)"
            />
          </td>
        </tr>
      </tbody>
    </table>

    <template v-if="tipoActivo === 'subtemas' && puedeGestionar">
      <hr />
      <h2 class="eca-titulo">Nuevo subtema</h2>
      <div class="catalogos__nuevo">
        <select v-model="nuevoSubtemaTemaId">
          <option :value="null" disabled>Selecciona un tema</option>
          <option v-for="t in temas" :key="t.id" :value="t.id">{{ t.nombre }}</option>
        </select>
        <input v-model="nuevoSubtemaClave" placeholder="Clave" />
        <input v-model="nuevoSubtemaNombre" placeholder="Nombre" />
        <button type="button" class="eca-btn eca-btn-primary" :disabled="creandoSubtema" @click="onCrearSubtema">
          {{ creandoSubtema ? 'Creando…' : 'Crear subtema' }}
        </button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.catalogos__tabs {
  display: flex;
  gap: 0.5rem;
  margin: 1rem 0;
  flex-wrap: wrap;
}
.catalogos__tab--activo {
  background: var(--eca-purple-600);
  color: #fff;
  border-color: var(--eca-purple-600);
}
.catalogos__nuevo {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}
.catalogos__nuevo select,
.catalogos__nuevo input {
  padding: 0.5rem 0.7rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
}
</style>
