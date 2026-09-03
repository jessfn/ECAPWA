<!-- pwa-eca — pantalla "Nueva actividad" (ECA-013). Rediseño pedido
     explícito: mismo lenguaje visual que el cuestionario de actividades
     de pwasuper — tarjetas de "paso" numeradas con acento morado, badge
     "Listo" cuando el paso ya está completo, checklist de resumen antes
     de enviar. Los CAMPOS y su lógica de validación (catálogo real de
     ECA: modalidad/tipo/tema/subtema/sistema productivo/ECA/fotos) NO
     cambiaron — pwasuper solo tiene un cuestionario genérico de
     modalidad Campo/Gabinete + categoría fija, mucho más simple que el
     de este proyecto; lo que se copia es el DISEÑO de los pasos, no los
     campos. Las reglas de catálogo (requiere_eca, permite_participantes,
     tema/subtema) solo se reflejan aquí para UX — el backend las vuelve
     a validar siempre. -->
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
import AuthIcon from '../components/auth/AuthIcon.vue'
import AvisoModal from '../components/AvisoModal.vue'

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
const avisoExito = ref(false)
const gps = ref(null)
const fotos = ref([])
const errorFotos = ref('')

const tipoSeleccionado = computed(
  () => catalogos.value?.tiposActividad.find((t) => t.id === tipoActividadId.value) || null,
)
const subtemasDisponibles = computed(() =>
  catalogos.value && temaId.value ? subtemasDelTema(catalogos.value, temaId.value) : [],
)
const minFotos = computed(() => (tipoSeleccionado.value?.requiere_evidencia ? tipoSeleccionado.value.min_fotos : 0))

// Estado "Listo" de cada paso — mismo patrón visual que el checklist de
// pwasuper, adaptado a los campos reales de este proyecto.
// `gps` siempre queda con un objeto tras el primer intento (incluso
// SIN_GPS/permiso denegado) — "Listo" debe reflejar que en verdad se
// obtuvo una lectura real, no solo que ya se intentó.
const pasoUbicacionListo = computed(() => gps.value?.estado_gps === 'CON_GPS' || gps.value?.estado_gps === 'GPS_IMPRECISO')
const pasoClasificacionListo = computed(
  () => Boolean(modalidadId.value) && Boolean(tipoActividadId.value) && (!tipoSeleccionado.value?.requiere_eca || Boolean(ecaId.value)),
)
const pasoDescripcionListo = computed(() => Boolean(descripcion.value.trim()))
const pasoFotosListo = computed(() => !minFotos.value || fotos.value.length >= minFotos.value)
const todoListo = computed(
  () => pasoUbicacionListo.value && pasoClasificacionListo.value && pasoDescripcionListo.value && pasoFotosListo.value,
)

// Mismo criterio que en JornadaView: el mensaje solo debe hablar de "sin
// señal" cuando de verdad no la hay — antes salía igual con internet.
const mensajeConfirmacion = computed(() => {
  const sync = actividad.ultimoSync
  if (sync?.motivo === 'sin_red') {
    return 'Tu actividad se guardó en tu dispositivo. En cuanto tengas señal, se subirá automáticamente al servidor.'
  }
  if (sync?.ok && (sync.aplicados > 0 || sync.duplicados > 0)) {
    return 'Tu actividad se guardó y ya se sincronizó con el servidor.'
  }
  return 'Tu actividad se guardó en tu dispositivo. La reintentaremos en breve.'
})

onMounted(async () => {
  catalogos.value = await obtenerCatalogos()
  if (!jornada.actual) {
    await jornada.cargarHoy()
  }
})

async function guardar() {
  actividad.error = ''
  errorFotos.value = ''

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

  if (minFotos.value && fotos.value.length < minFotos.value) {
    errorFotos.value = `Este tipo de actividad requiere al menos ${minFotos.value} foto(s).`
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

    // Antes se navegaba a Inicio en el mismo instante que se ponía el
    // mensaje de éxito — el usuario casi nunca alcanzaba a verlo. Ahora
    // un modal de confirmación bloquea la pantalla hasta que el usuario
    // lo cierra, y solo entonces se navega (`cerrarAvisoExito`).
    avisoExito.value = true
  } catch {
    // el mensaje ya quedó en actividad.error
  }
}

function cerrarAvisoExito() {
  avisoExito.value = false
  router.push({ name: 'inicio' })
}
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <div class="eca-card eca-entrar" style="--eca-delay: 0.06s">
      <h1 class="eca-titulo">Nueva actividad</h1>
      <p class="eca-ayuda">Registra qué hiciste, dónde y con qué evidencia.</p>

      <p v-if="!jornada.abierta" class="eca-alerta-aviso">
        Necesitas una jornada abierta para registrar una actividad.
        <RouterLink :to="{ name: 'jornada' }">Ir a Jornada</RouterLink>
      </p>

      <form v-else-if="catalogos" class="nueva-actividad" @submit.prevent="guardar">
        <p v-if="actividad.error" class="eca-alerta-error" role="alert">{{ actividad.error }}</p>

        <!-- Paso 1: Ubicación -->
        <section class="nueva-actividad__paso">
          <header class="nueva-actividad__paso-cabecera">
            <span class="nueva-actividad__paso-numero">1</span>
            <h2 class="nueva-actividad__paso-titulo">Ubicación</h2>
            <span v-if="pasoUbicacionListo" class="nueva-actividad__completado">
              <AuthIcon name="check" /> Listo
            </span>
          </header>
          <CapturaGps @capturado="(g) => (gps = g)" />
        </section>

        <!-- Paso 2: Clasificación -->
        <section class="nueva-actividad__paso">
          <header class="nueva-actividad__paso-cabecera">
            <span class="nueva-actividad__paso-numero">2</span>
            <h2 class="nueva-actividad__paso-titulo">Clasificación</h2>
            <span v-if="pasoClasificacionListo" class="nueva-actividad__completado">
              <AuthIcon name="check" /> Listo
            </span>
          </header>

          <label>
            Modalidad
            <select v-model="modalidadId" class="nueva-actividad__select" required>
              <option :value="null" disabled>Selecciona…</option>
              <option v-for="m in catalogos.modalidades" :key="m.id" :value="m.id">{{ m.nombre }}</option>
            </select>
          </label>

          <label>
            Tipo de actividad
            <select v-model="tipoActividadId" class="nueva-actividad__select" required>
              <option :value="null" disabled>Selecciona…</option>
              <option v-for="t in catalogos.tiposActividad" :key="t.id" :value="t.id">{{ t.nombre }}</option>
            </select>
          </label>

          <label>
            Tema (opcional)
            <select v-model="temaId" class="nueva-actividad__select" @change="subtemaId = null">
              <option :value="null">Sin tema</option>
              <option v-for="t in catalogos.temas" :key="t.id" :value="t.id">{{ t.nombre }}</option>
            </select>
          </label>

          <label v-if="temaId">
            Subtema (opcional)
            <select v-model="subtemaId" class="nueva-actividad__select">
              <option :value="null">Sin subtema</option>
              <option v-for="s in subtemasDisponibles" :key="s.id" :value="s.id">{{ s.nombre }}</option>
            </select>
          </label>

          <label>
            Sistema productivo (opcional)
            <select v-model="sistemaProductivoId" class="nueva-actividad__select">
              <option :value="null">Sin sistema productivo</option>
              <option v-for="s in catalogos.sistemasProductivos" :key="s.id" :value="s.id">{{ s.nombre }}</option>
            </select>
          </label>

          <fieldset v-if="tipoSeleccionado?.requiere_eca">
            <legend>ECA (requerida)</legend>
            <SelectorEca v-model="ecaId" />
          </fieldset>
        </section>

        <!-- Paso 3: Descripción -->
        <section class="nueva-actividad__paso">
          <header class="nueva-actividad__paso-cabecera">
            <span class="nueva-actividad__paso-numero">3</span>
            <h2 class="nueva-actividad__paso-titulo">Descripción</h2>
            <span v-if="pasoDescripcionListo" class="nueva-actividad__completado">
              <AuthIcon name="check" /> Listo
            </span>
          </header>

          <label>
            Descripción
            <textarea v-model="descripcion" class="nueva-actividad__textarea" required rows="4" />
          </label>

          <label>
            Resultado (opcional)
            <textarea v-model="resultado" class="nueva-actividad__textarea" rows="3" />
          </label>

          <label v-if="tipoSeleccionado?.permite_participantes">
            Número de participantes
            <input v-model.number="numParticipantes" class="nueva-actividad__select" type="number" min="0" />
          </label>

          <label class="nueva-actividad__checkbox">
            <input v-model="requiereSeguimiento" type="checkbox" />
            Requiere seguimiento
          </label>

          <label v-if="requiereSeguimiento">
            Fecha de próximo seguimiento
            <input v-model="fechaProximoSeguimiento" class="nueva-actividad__select" type="date" />
          </label>
        </section>

        <!-- Paso 4: Evidencia fotográfica -->
        <section v-if="tipoSeleccionado" class="nueva-actividad__paso">
          <header class="nueva-actividad__paso-cabecera">
            <span class="nueva-actividad__paso-numero">4</span>
            <h2 class="nueva-actividad__paso-titulo">
              Evidencia fotográfica
              <span class="nueva-actividad__paso-subtitulo">
                {{ tipoSeleccionado.requiere_evidencia ? `mínimo ${tipoSeleccionado.min_fotos}` : 'opcional' }}
              </span>
            </h2>
            <span v-if="pasoFotosListo" class="nueva-actividad__completado">
              <AuthIcon name="check" /> Listo
            </span>
          </header>
          <p v-if="errorFotos" class="eca-alerta-error" role="alert">{{ errorFotos }}</p>
          <CapturaEvidencia
            :min-fotos="minFotos"
            :max-fotos="tipoSeleccionado.max_fotos"
            @update:fotos="(f) => (fotos = f)"
          />
        </section>

        <!-- Checklist de resumen — mismo patrón que pwasuper: un vistazo
             rápido a qué falta antes de intentar enviar. -->
        <div class="nueva-actividad__checklist">
          <div class="nueva-actividad__check-item" :class="{ 'nueva-actividad__check-item--listo': pasoUbicacionListo }">
            <span class="nueva-actividad__check-circulo"><AuthIcon v-if="pasoUbicacionListo" name="check" /></span>
            Ubicación
          </div>
          <div class="nueva-actividad__check-item" :class="{ 'nueva-actividad__check-item--listo': pasoClasificacionListo }">
            <span class="nueva-actividad__check-circulo"><AuthIcon v-if="pasoClasificacionListo" name="check" /></span>
            Clasificación
          </div>
          <div class="nueva-actividad__check-item" :class="{ 'nueva-actividad__check-item--listo': pasoDescripcionListo }">
            <span class="nueva-actividad__check-circulo"><AuthIcon v-if="pasoDescripcionListo" name="check" /></span>
            Descripción
          </div>
          <div v-if="tipoSeleccionado" class="nueva-actividad__check-item" :class="{ 'nueva-actividad__check-item--listo': pasoFotosListo }">
            <span class="nueva-actividad__check-circulo"><AuthIcon v-if="pasoFotosListo" name="check" /></span>
            Evidencia
          </div>
        </div>

        <p v-if="todoListo" class="nueva-actividad__listo">
          <AuthIcon name="check" /> Todo listo para enviar
        </p>

        <button type="submit" class="eca-btn eca-btn-primary" :disabled="actividad.guardando || !jornada.abierta">
          {{ actividad.guardando ? 'Guardando…' : 'Guardar actividad' }}
        </button>
      </form>
    </div>

    <AvisoModal
      v-if="avisoExito"
      tipo="exito"
      titulo="Actividad guardada"
      :mensaje="mensajeConfirmacion"
      @cerrar="cerrarAvisoExito"
    />
  </main>
</template>

<style scoped>
.nueva-actividad {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.nueva-actividad label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--eca-ink-soft);
  margin-bottom: 0.7rem;
}
.nueva-actividad label:last-child {
  margin-bottom: 0;
}
.nueva-actividad__checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
fieldset {
  border: none;
  padding: 0;
  margin: 0 0 0.7rem;
}
fieldset legend {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--eca-ink-soft);
  padding: 0 0 0.3rem;
}

/* Tarjeta de "paso" — mismo lenguaje visual que `apple-step-card-purple`
   de pwasuper: acento morado sutil, número circular, badge "Listo". */
.nueva-actividad__paso {
  background: linear-gradient(180deg, #ffffff 0%, #fdfaff 100%);
  border: 1px solid rgba(147, 51, 234, 0.15);
  border-radius: var(--eca-r-lg);
  padding: 1rem 1.1rem;
}
.nueva-actividad__paso-cabecera {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.9rem;
}
.nueva-actividad__paso-numero {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #9333ea 0%, #7c3aed 100%);
  color: #fff;
  font-size: 0.8rem;
  font-weight: 800;
}
.nueva-actividad__paso-titulo {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--eca-ink);
  flex: 1;
}
.nueva-actividad__paso-subtitulo {
  display: block;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--eca-ink-soft);
  margin-top: 0.1rem;
}
.nueva-actividad__completado {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--eca-green-700);
  background: var(--eca-green-100);
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  flex-shrink: 0;
}
.nueva-actividad__completado svg {
  width: 11px;
  height: 11px;
}

/* Inputs con acento morado al enfocar — igual que `.apple-select`/
   `.apple-textarea` de pwasuper. */
.nueva-actividad__select,
.nueva-actividad__textarea {
  width: 100%;
  padding: 0.6rem 0.75rem;
  border-radius: var(--eca-r-sm);
  border: 1.5px solid var(--eca-surface-border);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 400;
  color: var(--eca-ink);
  background: #fff;
}
.nueva-actividad__textarea {
  resize: vertical;
}
.nueva-actividad__select:focus,
.nueva-actividad__textarea:focus {
  outline: none;
  border-color: #9333ea;
  box-shadow: 0 0 0 3px rgba(147, 51, 234, 0.15);
}

/* Checklist de resumen. */
.nueva-actividad__checklist {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
  gap: 0.5rem;
  background: var(--eca-surface);
  border-radius: var(--eca-r-md);
  padding: 0.75rem;
}
.nueva-actividad__check-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--eca-ink-faint);
}
.nueva-actividad__check-item--listo {
  color: var(--eca-ink);
}
.nueva-actividad__check-circulo {
  flex-shrink: 0;
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 50%;
  border: 1.5px solid var(--eca-surface-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.nueva-actividad__check-item--listo .nueva-actividad__check-circulo {
  background: var(--eca-green-600);
  border-color: var(--eca-green-600);
}
.nueva-actividad__check-circulo svg {
  width: 10px;
  height: 10px;
}

.nueva-actividad__listo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  margin: 0;
  padding: 0.7rem;
  border-radius: var(--eca-r-md);
  background: var(--eca-green-100);
  color: var(--eca-green-800);
  font-weight: 700;
  font-size: 0.85rem;
}
.nueva-actividad__listo svg {
  width: 16px;
  height: 16px;
}
</style>
