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
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useJornadaStore } from '../stores/jornada'
import { useActividadStore } from '../stores/actividad'
import { obtenerCatalogos, subtemasDelTema } from '../services/catalogosCache'
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
// Pedido explícito (2026-09-03): la ECA se escribe a mano en vez de
// elegirse de un selector — muchos técnicos no tienen ninguna ECA en su
// catálogo/ámbito todavía y el selector los dejaba sin poder guardar
// ninguna actividad que la requiriera.
// Pedido explícito (2026-09-08): la ECA es SIEMPRE obligatoria (antes solo
// lo era si el tipo de actividad la exigía) y se escribe/guarda siempre en
// MAYÚSCULAS y SIN TILDES — se transforma mientras el técnico teclea, no
// solo al enviar, para que lo que ve en pantalla sea igual a lo que se
// guarda (backend refuerza lo mismo por si acaso, ver `_normalizar_eca`).
const ecaNombre = ref('')
// Solo quita el acento de las vocales (á/é/í/ó/ú/ü) — la "ñ" NO se toca:
// es una letra propia del español, no una "n acentuada", y un `normalize
// ('NFD')` genérico la convertía en "N" (bug real: "Muñoz" -> "MUNOZ",
// "Peña" -> "PENA"), corrompiendo nombres de lugar comunes en México.
// Reutilizada tanto para la ECA escrita a mano como para el texto de
// cualquier opción "Otro" de los catálogos (mismo criterio, mismo bug a
// evitar).
const MAPA_ACENTOS = { á: 'a', é: 'e', í: 'i', ó: 'o', ú: 'u', ü: 'u' }
function normalizarMayusculasSinTildes(texto) {
  return (texto || '')
    .toLowerCase()
    .replace(/[áéíóúü]/g, (c) => MAPA_ACENTOS[c])
    .toUpperCase()
}
// Fábrica de manejador de `@input`: mueve el texto normalizado al `ref`
// destino preservando la posición del cursor. La normalización (mayúsculas
// + quitar acento) es 1 carácter -> 1 carácter, así que el cursor casi
// siempre queda en el mismo índice — pero Vue reasigna `value` del input, y
// el navegador por defecto manda el cursor al final del texto si no se
// restaura a mano.
function crearManejadorMayusculas(destino) {
  return (evento) => {
    const cursor = evento.target.selectionStart
    destino.value = normalizarMayusculasSinTildes(evento.target.value)
    requestAnimationFrame(() => evento.target.setSelectionRange(cursor, cursor))
  }
}
const onInputEca = crearManejadorMayusculas(ecaNombre)

// Pedido explícito: cuando el técnico elige la opción "Otro" en tipo de
// actividad, tema, subtema o sistema productivo, debe escribir
// obligatoriamente cuál es ese "otro" — antes se guardaba solo "Otro" sin
// que el admin supiera a qué se refería. Clave "OTR" en tipos_actividad,
// "OTRO" en temas/subtemas/sistemas_productivos (ver `0012_seed_catalogos`
// en el backend).
const tipoActividadOtroTexto = ref('')
const temaOtroTexto = ref('')
const subtemaOtroTexto = ref('')
const sistemaProductivoOtroTexto = ref('')
const onInputTipoOtro = crearManejadorMayusculas(tipoActividadOtroTexto)
const onInputTemaOtro = crearManejadorMayusculas(temaOtroTexto)
const onInputSubtemaOtro = crearManejadorMayusculas(subtemaOtroTexto)
const onInputSistemaOtro = crearManejadorMayusculas(sistemaProductivoOtroTexto)

const temaSeleccionado = computed(() => catalogos.value?.temas.find((t) => t.id === temaId.value) || null)
const subtemaSeleccionado = computed(() => subtemasDisponibles.value.find((s) => s.id === subtemaId.value) || null)
const sistemaProductivoSeleccionado = computed(
  () => catalogos.value?.sistemasProductivos.find((s) => s.id === sistemaProductivoId.value) || null,
)
const esTipoOtro = computed(() => tipoSeleccionado.value?.clave === 'OTR')
const esTemaOtro = computed(() => temaSeleccionado.value?.clave === 'OTRO')
const esSubtemaOtro = computed(() => subtemaSeleccionado.value?.clave === 'OTRO')
const esSistemaProductivoOtro = computed(() => sistemaProductivoSeleccionado.value?.clave === 'OTRO')

// Si el técnico cambia de opción y ya no es "Otro", se limpia el texto que
// había escrito — si no, quedaría un texto huérfano listo para colarse si
// vuelve a elegir "Otro" sin querer escribir uno nuevo.
watch(tipoActividadId, () => {
  if (!esTipoOtro.value) tipoActividadOtroTexto.value = ''
})
watch(temaId, () => {
  if (!esTemaOtro.value) temaOtroTexto.value = ''
})
watch(subtemaId, () => {
  if (!esSubtemaOtro.value) subtemaOtroTexto.value = ''
})
watch(sistemaProductivoId, () => {
  if (!esSistemaProductivoOtro.value) sistemaProductivoOtroTexto.value = ''
})
const descripcion = ref('')
const resultado = ref('')
const numParticipantes = ref(null)
const requiereSeguimiento = ref(false)
const fechaProximoSeguimiento = ref('')
const avisoExito = ref(false)
const gps = ref(null)
const fotos = ref([])
const errorFotos = ref('')
// Candado de reentrada: evita que un doble toque en "Guardar" cree DOS
// actividades (cada llamada a `actividad.crear` genera un uuid nuevo, así
// que el backend no puede deduplicarlas — se veían como filas duplicadas
// en admin). Se pone en true de forma síncrona al entrar a `guardar`,
// antes de cualquier `await`, y solo se libera si hubo error (en éxito se
// navega fuera de la pantalla).
const enviando = ref(false)

const tipoSeleccionado = computed(
  () => catalogos.value?.tiposActividad.find((t) => t.id === tipoActividadId.value) || null,
)
const subtemasDisponibles = computed(() =>
  catalogos.value && temaId.value ? subtemasDelTema(catalogos.value, temaId.value) : [],
)
// Pedido explícito (2026-09-03): al menos 1 foto es obligatoria SIEMPRE,
// sin importar lo que diga el catálogo — antes un tipo con
// `requiere_evidencia=false` (p. ej. "Organización de productores",
// "Gestión", "Otro") dejaba mandar la actividad sin ninguna evidencia.
// Si el catálogo pide más de 1, se respeta ese mínimo mayor.
const minFotos = computed(() =>
  Math.max(1, tipoSeleccionado.value?.requiere_evidencia ? tipoSeleccionado.value.min_fotos : 0),
)

// Estado "Listo" de cada paso — mismo patrón visual que el checklist de
// pwasuper, adaptado a los campos reales de este proyecto.
// `gps` siempre queda con un objeto tras el primer intento (incluso
// SIN_GPS/permiso denegado) — "Listo" debe reflejar que en verdad se
// obtuvo una lectura real, no solo que ya se intentó.
const pasoUbicacionListo = computed(() => gps.value?.estado_gps === 'CON_GPS' || gps.value?.estado_gps === 'GPS_IMPRECISO')
const pasoClasificacionListo = computed(
  () =>
    Boolean(modalidadId.value) &&
    Boolean(tipoActividadId.value) &&
    Boolean(ecaNombre.value.trim()) &&
    (!esTipoOtro.value || Boolean(tipoActividadOtroTexto.value.trim())) &&
    (!esTemaOtro.value || Boolean(temaOtroTexto.value.trim())) &&
    (!esSubtemaOtro.value || Boolean(subtemaOtroTexto.value.trim())) &&
    (!esSistemaProductivoOtro.value || Boolean(sistemaProductivoOtroTexto.value.trim())),
)
const pasoDescripcionListo = computed(() => Boolean(descripcion.value.trim()))
const pasoFotosListo = computed(() => !minFotos.value || fotos.value.length >= minFotos.value)
const todoListo = computed(
  () => pasoUbicacionListo.value && pasoClasificacionListo.value && pasoDescripcionListo.value && pasoFotosListo.value,
)

// Mismo criterio que en JornadaView: el mensaje solo debe hablar de "sin
// señal" cuando de verdad no la hay — antes salía igual con internet.
//
// Bug real encontrado en producción: cuando la actividad lleva foto, esta
// pantalla dispara DOS sincronizaciones seguidas — una al crear la
// actividad (`actividad.crear`) y otra al encolar la evidencia
// (`actividad.encolarEvidencias`) — y `actividad.ultimoSync` solo guarda
// el resultado de la SEGUNDA. Esa segunda sincronización solo mueve
// evidencias (no jornadas/actividades), así que `aplicados`/`duplicados`
// siempre quedan en 0 aunque la foto SÍ se haya subido con éxito — el
// mensaje decía "la reintentaremos en breve" incluso cuando todo ya
// estaba en el servidor. Confirmado subiendo una actividad de prueba
// real: la evidencia llegó al servidor pese al mensaje. Con `sync?.ok`
// alcanza: cualquier sincronización exitosa (con o sin conteo de
// aplicados/duplicados) significa que ya no queda nada pendiente.
const mensajeConfirmacion = computed(() => {
  const sync = actividad.ultimoSync
  if (sync?.motivo === 'sin_red') {
    return 'Tu actividad se guardó en tu dispositivo. En cuanto tengas señal, se subirá automáticamente al servidor.'
  }
  if (sync?.ok) {
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
  // Candado síncrono: si ya hay un envío en curso, ignorar el segundo toque.
  if (enviando.value) return
  enviando.value = true
  actividad.error = ''
  errorFotos.value = ''

  // Ubicación OBLIGATORIA (pedido explícito): no se puede subir una
  // actividad sin una lectura de GPS real (CON_GPS o GPS_IMPRECISO). Sin
  // esto, el técnico podía guardar con estado SIN_GPS y quedaba sin
  // coordenadas.
  if (!pasoUbicacionListo.value) {
    actividad.error = 'Debes capturar la ubicación (GPS) antes de guardar la actividad.'
    enviando.value = false
    return
  }

  // Antes, si la jornada no estaba abierta en ESTE dispositivo (p. ej.
  // se inició desde otro), esto tronaba en silencio al leer
  // `jornada.actual.uuid` de `null` — el catch de abajo lo atrapaba sin
  // avisar y en pantalla quedaba el error de un intento previo, muy
  // confuso ("no se guarda"). `jornada.cargarHoy()` ya se llama al
  // montar la vista y trae la verdad del servidor; si aun así no hay
  // jornada abierta, se corta aquí con un mensaje claro.
  if (!jornada.abierta) {
    actividad.error = 'Necesitas una jornada abierta para registrar una actividad.'
    enviando.value = false
    return
  }

  // ECA OBLIGATORIA (pedido explícito): toda actividad debe traer el
  // nombre de la ECA, sin importar el tipo. Ya viene en mayúsculas y sin
  // tildes desde que el técnico la escribió (`onInputEca`); `.trim()` solo
  // quita espacios sueltos al inicio/fin.
  if (!ecaNombre.value.trim()) {
    actividad.error = 'Escribe el nombre de la ECA antes de guardar la actividad.'
    enviando.value = false
    return
  }

  // "Otro" obligatorio (pedido explícito): si el técnico eligió "Otro" en
  // cualquiera de estos catálogos, debe escribir cuál es — si no, el admin
  // solo ve "Otro" en el listado sin saber a qué se refería.
  if (esTipoOtro.value && !tipoActividadOtroTexto.value.trim()) {
    actividad.error = 'Escribe cuál es el otro tipo de actividad.'
    enviando.value = false
    return
  }
  if (esTemaOtro.value && !temaOtroTexto.value.trim()) {
    actividad.error = 'Escribe cuál es el otro tema.'
    enviando.value = false
    return
  }
  if (esSubtemaOtro.value && !subtemaOtroTexto.value.trim()) {
    actividad.error = 'Escribe cuál es el otro subtema.'
    enviando.value = false
    return
  }
  if (esSistemaProductivoOtro.value && !sistemaProductivoOtroTexto.value.trim()) {
    actividad.error = 'Escribe cuál es el otro sistema productivo.'
    enviando.value = false
    return
  }

  if (minFotos.value && fotos.value.length < minFotos.value) {
    errorFotos.value = `Este tipo de actividad requiere al menos ${minFotos.value} foto(s).`
    enviando.value = false
    return
  }

  try {
    const nuevaActividad = await actividad.crear({
      jornadaUuid: jornada.actual.uuid,
      ecaNombre: ecaNombre.value.trim(),
      modalidadId: modalidadId.value,
      tipoActividadId: tipoActividadId.value,
      temaId: temaId.value,
      subtemaId: subtemaId.value,
      sistemaProductivoId: sistemaProductivoId.value,
      tipoActividadOtroTexto: esTipoOtro.value ? tipoActividadOtroTexto.value.trim() : null,
      temaOtroTexto: esTemaOtro.value ? temaOtroTexto.value.trim() : null,
      subtemaOtroTexto: esSubtemaOtro.value ? subtemaOtroTexto.value.trim() : null,
      sistemaProductivoOtroTexto: esSistemaProductivoOtro.value ? sistemaProductivoOtroTexto.value.trim() : null,
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
    // el mensaje ya quedó en actividad.error; se libera el candado para
    // permitir reintentar.
    enviando.value = false
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
          <label v-if="esTipoOtro">
            ¿Cuál es el otro tipo de actividad?
            <input
              :value="tipoActividadOtroTexto"
              type="text"
              class="nueva-actividad__select nueva-actividad__eca"
              placeholder="ESCRIBE CUÁL…"
              autocapitalize="characters"
              autocomplete="off"
              autocorrect="off"
              spellcheck="false"
              required
              @input="onInputTipoOtro"
            />
          </label>

          <label>
            Tema (opcional)
            <select v-model="temaId" class="nueva-actividad__select" @change="subtemaId = null">
              <option :value="null">Sin tema</option>
              <option v-for="t in catalogos.temas" :key="t.id" :value="t.id">{{ t.nombre }}</option>
            </select>
          </label>
          <label v-if="esTemaOtro">
            ¿Cuál es el otro tema?
            <input
              :value="temaOtroTexto"
              type="text"
              class="nueva-actividad__select nueva-actividad__eca"
              placeholder="ESCRIBE CUÁL…"
              autocapitalize="characters"
              autocomplete="off"
              autocorrect="off"
              spellcheck="false"
              required
              @input="onInputTemaOtro"
            />
          </label>

          <label v-if="temaId">
            Subtema (opcional)
            <select v-model="subtemaId" class="nueva-actividad__select">
              <option :value="null">Sin subtema</option>
              <option v-for="s in subtemasDisponibles" :key="s.id" :value="s.id">{{ s.nombre }}</option>
            </select>
          </label>
          <label v-if="esSubtemaOtro">
            ¿Cuál es el otro subtema?
            <input
              :value="subtemaOtroTexto"
              type="text"
              class="nueva-actividad__select nueva-actividad__eca"
              placeholder="ESCRIBE CUÁL…"
              autocapitalize="characters"
              autocomplete="off"
              autocorrect="off"
              spellcheck="false"
              required
              @input="onInputSubtemaOtro"
            />
          </label>

          <label>
            Sistema productivo (opcional)
            <select v-model="sistemaProductivoId" class="nueva-actividad__select">
              <option :value="null">Sin sistema productivo</option>
              <option v-for="s in catalogos.sistemasProductivos" :key="s.id" :value="s.id">{{ s.nombre }}</option>
            </select>
          </label>
          <label v-if="esSistemaProductivoOtro">
            ¿Cuál es el otro sistema productivo?
            <input
              :value="sistemaProductivoOtroTexto"
              type="text"
              class="nueva-actividad__select nueva-actividad__eca"
              placeholder="ESCRIBE CUÁL…"
              autocapitalize="characters"
              autocomplete="off"
              autocorrect="off"
              spellcheck="false"
              required
              @input="onInputSistemaOtro"
            />
          </label>

          <label>
            ECA (obligatoria)
            <input
              :value="ecaNombre"
              type="text"
              class="nueva-actividad__select nueva-actividad__eca"
              placeholder="ESCRIBE EL NOMBRE DE LA ECA…"
              autocapitalize="characters"
              autocomplete="off"
              autocorrect="off"
              spellcheck="false"
              required
              @input="onInputEca"
            />
          </label>
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
              <span class="nueva-actividad__paso-subtitulo">mínimo {{ minFotos }} (obligatoria)</span>
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

        <button
          type="submit"
          class="eca-btn eca-btn-primary"
          :disabled="enviando || actividad.guardando || !jornada.abierta || !pasoUbicacionListo"
        >
          {{ enviando || actividad.guardando ? 'Guardando…' : 'Guardar actividad' }}
        </button>
        <p v-if="!pasoUbicacionListo" class="eca-ayuda" style="text-align:center;margin:0">
          Captura tu ubicación (paso 1) para poder guardar.
        </p>
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
/* La transformación real (mayúsculas + sin tildes) la hace `onInputEca` en
   JS — esto solo asegura que, mientras el navegador repinta, el texto ya
   se VEA en mayúsculas (evita un parpadeo con minúsculas de por medio). */
.nueva-actividad__eca {
  text-transform: uppercase;
  letter-spacing: 0.02em;
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
