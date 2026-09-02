<!-- pwa-eca — pantalla "Nueva actividad" (ECA-013). Sin GPS ni fotos
     todavía (ECA-014/ECA-015). Las reglas de catálogo (requiere_eca,
     permite_participantes, tema/subtema) solo se reflejan aquí para UX —
     el backend las vuelve a validar siempre. -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useJornadaStore } from '../stores/jornada'
import { useActividadStore } from '../stores/actividad'
import { obtenerCatalogos, subtemasDelTema } from '../services/catalogosCache'
import SelectorEca from '../components/SelectorEca.vue'
import CapturaGps from '../components/CapturaGps.vue'
import CapturaEvidencia from '../components/CapturaEvidencia.vue'
import BackButton from '../components/BackButton.vue'

const router = useRouter()
const jornada = useJornadaStore()
const actividad = useActividadStore()

const catalogos = ref(null)
const modalidadId = ref(null)
const tipoActividadId = ref(null)
const temaId = ref(null)
const subtemaId = ref(null)
const sistemaProductivoId = ref(null)
const ecaId = ref(null)
const descripcion = ref('')
const resultado = ref('')
const numParticipantes = ref(null)
const requiereSeguimiento = ref(false)
const fechaProximoSeguimiento = ref('')
const mensaje = ref('')
const gps = ref(null)
const fotos = ref([])
const errorFotos = ref('')

const tipoSeleccionado = computed(
  () => catalogos.value?.tiposActividad.find((t) => t.id === tipoActividadId.value) || null,
)
const subtemasDisponibles = computed(() =>
  catalogos.value && temaId.value ? subtemasDelTema(catalogos.value, temaId.value) : [],
)

onMounted(async () => {
  catalogos.value = await obtenerCatalogos()
  if (!jornada.actual) {
    await jornada.cargarHoy()
  }
})

async function guardar() {
  actividad.error = ''
  errorFotos.value = ''
  mensaje.value = ''

  // Antes, si la jornada no estaba abierta en ESTE dispositivo (p. ej.
  // se inició desde otro), esto tronaba en silencio al leer
  // `jornada.actual.uuid` de `null` — el catch de abajo lo atrapaba sin
  // avisar y en pantalla quedaba el error de un intento previo, muy
  // confuso ("no se guarda"). `jornada.cargarHoy()` ya se llama al
  // montar la vista y trae la verdad del servidor; si aun así no hay
  // jornada abierta, se corta aquí con un mensaje claro.
  if (!jornada.abierta) {
    actividad.error = 'Necesitas una jornada abierta para registrar una actividad.'
    return
  }

  const minFotos = tipoSeleccionado.value?.requiere_evidencia ? tipoSeleccionado.value.min_fotos : 0
  if (minFotos && fotos.value.length < minFotos) {
    errorFotos.value = `Este tipo de actividad requiere al menos ${minFotos} foto(s).`
    return
  }

  try {
    const nuevaActividad = await actividad.crear({
      jornadaUuid: jornada.actual.uuid,
      ecaId: ecaId.value,
      modalidadId: modalidadId.value,
      tipoActividadId: tipoActividadId.value,
      temaId: temaId.value,
      subtemaId: subtemaId.value,
      sistemaProductivoId: sistemaProductivoId.value,
      descripcion: descripcion.value,
      resultado: resultado.value || null,
      numParticipantes: tipoSeleccionado.value?.permite_participantes ? numParticipantes.value : null,
      requiereSeguimiento: requiereSeguimiento.value,
      fechaProximoSeguimiento: requiereSeguimiento.value ? fechaProximoSeguimiento.value || null : null,
      gps: gps.value,
    })

    if (fotos.value.length) {
      await actividad.encolarEvidencias(nuevaActividad.uuid, fotos.value, gps.value)
    }

    mensaje.value = 'Actividad guardada en el dispositivo. Se sincronizará cuando haya red.'
    router.push({ name: 'inicio' })
  } catch {
    // el mensaje ya quedó en actividad.error
  }
}
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <div class="eca-card eca-entrar" style="--eca-delay: 0.06s">
      <h1 class="eca-titulo">Nueva actividad</h1>

      <p v-if="!jornada.abierta" class="eca-alerta-aviso">
        Necesitas una jornada abierta para registrar una actividad.
        <RouterLink :to="{ name: 'jornada' }">Ir a Jornada</RouterLink>
      </p>

    <form v-else-if="catalogos" class="eca-form" @submit.prevent="guardar">
      <p v-if="actividad.error" class="eca-alerta-error" role="alert">{{ actividad.error }}</p>

      <CapturaGps @capturado="(g) => (gps = g)" />

      <label>
        Modalidad
        <select v-model="modalidadId" required>
          <option :value="null" disabled>Selecciona…</option>
          <option v-for="m in catalogos.modalidades" :key="m.id" :value="m.id">{{ m.nombre }}</option>
        </select>
      </label>

      <label>
        Tipo de actividad
        <select v-model="tipoActividadId" required>
          <option :value="null" disabled>Selecciona…</option>
          <option v-for="t in catalogos.tiposActividad" :key="t.id" :value="t.id">{{ t.nombre }}</option>
        </select>
      </label>

      <label>
        Tema (opcional)
        <select v-model="temaId" @change="subtemaId = null">
          <option :value="null">Sin tema</option>
          <option v-for="t in catalogos.temas" :key="t.id" :value="t.id">{{ t.nombre }}</option>
        </select>
      </label>

      <label v-if="temaId">
        Subtema (opcional)
        <select v-model="subtemaId">
          <option :value="null">Sin subtema</option>
          <option v-for="s in subtemasDisponibles" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </label>

      <label>
        Sistema productivo (opcional)
        <select v-model="sistemaProductivoId">
          <option :value="null">Sin sistema productivo</option>
          <option v-for="s in catalogos.sistemasProductivos" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
      </label>

      <fieldset v-if="tipoSeleccionado?.requiere_eca">
        <legend>ECA {{ tipoSeleccionado.requiere_eca ? '(requerida)' : '(opcional)' }}</legend>
        <SelectorEca v-model="ecaId" />
      </fieldset>

      <label>
        Descripción
        <textarea v-model="descripcion" required rows="4" />
      </label>

      <label>
        Resultado (opcional)
        <textarea v-model="resultado" rows="3" />
      </label>

      <label v-if="tipoSeleccionado?.permite_participantes">
        Número de participantes
        <input v-model.number="numParticipantes" type="number" min="0" />
      </label>

      <label class="nueva-actividad__checkbox">
        <input v-model="requiereSeguimiento" type="checkbox" />
        Requiere seguimiento
      </label>

      <label v-if="requiereSeguimiento">
        Fecha de próximo seguimiento
        <input v-model="fechaProximoSeguimiento" type="date" />
      </label>

      <fieldset v-if="tipoSeleccionado" class="nueva-actividad__fieldset">
        <legend>Fotos {{ tipoSeleccionado.requiere_evidencia ? `(mínimo ${tipoSeleccionado.min_fotos})` : '(opcional)' }}</legend>
        <p v-if="errorFotos" class="eca-alerta-error" role="alert">{{ errorFotos }}</p>
        <CapturaEvidencia
          :min-fotos="tipoSeleccionado.requiere_evidencia ? tipoSeleccionado.min_fotos : 0"
          :max-fotos="tipoSeleccionado.max_fotos"
          @update:fotos="(f) => (fotos = f)"
        />
      </fieldset>

      <p v-if="mensaje" class="eca-alerta-ok">{{ mensaje }}</p>

      <button type="submit" class="eca-btn eca-btn-primary" :disabled="actividad.guardando || !jornada.abierta">
        {{ actividad.guardando ? 'Guardando…' : 'Guardar actividad' }}
      </button>
    </form>
    </div>
  </main>
</template>

<style scoped>
.nueva-actividad__checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
.nueva-actividad__fieldset {
  border: 1px solid var(--eca-surface-border);
  border-radius: var(--eca-r-sm);
  padding: 0.75rem 0.9rem;
}
.nueva-actividad__fieldset legend {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--eca-ink-soft);
  padding: 0 0.3rem;
}
fieldset {
  border: none;
  padding: 0;
  margin: 0;
}
</style>
