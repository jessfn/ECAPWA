<!-- pwa-eca — modal de confirmación para iniciar/terminar jornada.
     Diseño y flujo de ubicación alineados a propósito con `pwasuper`
     (mismo botón circular tipo Apple con anillo de progreso, pulso de
     éxito y estados default/loading/success — pedido explícito de que
     "sean exactamente igual"), con UNA diferencia deliberada y confirmada
     con el usuario: si el GPS real no da señal, `services/gps.js` NUNCA
     inventa una coordenada de respaldo (pwasuper cae a CDMX) — siempre
     usa la lectura real más aproximada que haya conseguido, o admite
     abiertamente "sin ubicación" antes que guardar un dato falso en el
     registro de jornada. Se pide la ubicación automáticamente al abrir
     (igual que `iniciarAsistencia()` en pwasuper), se muestra fecha/hora
     en vivo, y solo entonces aparece el botón para confirmar. -->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { capturarGps } from '../services/gps'
import AuthIcon from './auth/AuthIcon.vue'

const props = defineProps({
  tipo: { type: String, required: true }, // 'inicio' | 'fin'
})
const emit = defineEmits(['cancelar', 'confirmar'])

const FASE = { BUSCANDO: 'buscando', LISTO: 'listo', CONFIRMANDO: 'confirmando' }
const fase = ref(FASE.BUSCANDO)
const gps = ref(null)
const ahora = ref(new Date())
// Detalle obligatorio — pedido explícito: tanto iniciar como terminar
// jornada deben preguntar qué se hizo/pasó antes de dejar confirmar.
const nota = ref('')
const notaTocada = ref(false)

let temporizadorReloj = null

const textos = computed(() =>
  props.tipo === 'inicio'
    ? {
        titulo: 'Iniciar jornada',
        boton: 'Confirmar inicio',
        confirmando: 'Iniciando…',
        etiquetaNota: '¿Qué vas a hacer hoy?',
        placeholderNota: 'Ej. Visita a la ECA Los Encinos para dar seguimiento al cultivo de maíz…',
      }
    : {
        titulo: 'Terminar jornada',
        boton: 'Confirmar salida',
        confirmando: 'Terminando…',
        etiquetaNota: '¿Qué se hizo en la jornada?',
        placeholderNota: 'Ej. Se realizó la capacitación programada y se registraron 12 participantes…',
      },
)

const notaInvalida = computed(() => notaTocada.value && !nota.value.trim())
const puedeConfirmar = computed(
  () => fase.value === FASE.LISTO && Boolean(nota.value.trim()),
)

// Estado visual del botón de ubicación tipo Apple (ver `apple-location-btn`
// en pwasuper): loading mientras se busca, success con lectura real dentro
// del umbral de precisión, aviso si la lectura real es imprecisa, y un
// último estado si de plano no hubo ninguna lectura real.
const estadoGps = computed(() => {
  if (fase.value === FASE.BUSCANDO) {
    return { clase: 'jornada-ubicacion__boton--cargando', icono: 'map-pin', titulo: 'Obteniendo…', subtitulo: 'Espera un momento' }
  }
  const g = gps.value
  if (g?.estado_gps === 'CON_GPS') {
    return { clase: 'jornada-ubicacion__boton--lista', icono: 'check', titulo: 'Ubicación lista', subtitulo: 'Coordenadas capturadas' }
  }
  if (g?.estado_gps === 'GPS_IMPRECISO') {
    return {
      clase: 'jornada-ubicacion__boton--imprecisa',
      icono: 'map-pin',
      titulo: 'Ubicación aproximada',
      subtitulo: g.precision_gps_m ? `±${Math.round(g.precision_gps_m)} m de precisión` : 'Precisión limitada',
    }
  }
  return {
    clase: 'jornada-ubicacion__boton--sin-senal',
    icono: 'alert',
    titulo: 'Sin ubicación',
    subtitulo: g?.permiso_denegado ? 'Permiso denegado' : 'Toca para reintentar',
  }
})

const fechaFormateada = computed(() =>
  ahora.value.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
)
const horaFormateada = computed(() => ahora.value.toLocaleTimeString('es-MX'))

async function buscarUbicacion() {
  // Nota: no se guarda con "if fase===BUSCANDO return" — el estado inicial
  // YA es BUSCANDO (línea 18), así que ese guard cortaba la primera
  // captura automática de `onMounted` antes de llamar `capturarGps`,
  // dejando el modal colgado para siempre en "Obteniendo tu ubicación…".
  // El botón ya se deshabilita mientras `fase === FASE.BUSCANDO`
  // (`:disabled` en el template), así que no hace falta un guard aquí.
  fase.value = FASE.BUSCANDO
  gps.value = await capturarGps()
  fase.value = FASE.LISTO
}

async function confirmar() {
  notaTocada.value = true
  if (!nota.value.trim()) return
  fase.value = FASE.CONFIRMANDO
  // `gps` es un `ref()`: un objeto asignado a un ref se vuelve reactivo
  // (Proxy) automáticamente. IndexedDB no puede clonar un Proxy
  // (`DataCloneError` al hacer `put`) — se emite una copia plana.
  await emit('confirmar', { nota: nota.value.trim(), gps: gps.value ? { ...gps.value } : null })
}

onMounted(() => {
  buscarUbicacion()
  temporizadorReloj = setInterval(() => {
    ahora.value = new Date()
  }, 1000)
})
onUnmounted(() => {
  if (temporizadorReloj) clearInterval(temporizadorReloj)
})
</script>

<template>
  <Teleport to="body">
    <div class="jornada-modal__overlay" @click.self="emit('cancelar')">
      <div class="jornada-modal">
        <div class="jornada-modal__cabecera">
          <h2>{{ textos.titulo }}</h2>
          <button type="button" class="jornada-modal__cerrar" aria-label="Cerrar" @click="emit('cancelar')">
            <AuthIcon name="close" />
          </button>
        </div>

        <div class="jornada-ubicacion">
          <div class="jornada-ubicacion__envoltura">
            <button
              type="button"
              class="jornada-ubicacion__boton"
              :class="estadoGps.clase"
              :disabled="fase === FASE.BUSCANDO || fase === FASE.CONFIRMANDO"
              :aria-label="fase === FASE.BUSCANDO ? 'Obteniendo ubicación' : 'Obtener ubicación de nuevo'"
              @click="buscarUbicacion"
            >
              <span v-if="fase === FASE.BUSCANDO" class="jornada-ubicacion__anillo">
                <svg class="jornada-ubicacion__anillo-svg" viewBox="0 0 100 100">
                  <circle class="jornada-ubicacion__anillo-fondo" cx="50" cy="50" r="45" />
                  <circle class="jornada-ubicacion__anillo-progreso" cx="50" cy="50" r="45" />
                </svg>
              </span>
              <span v-if="gps?.estado_gps === 'CON_GPS' && fase === FASE.LISTO" class="jornada-ubicacion__pulso"></span>
              <span class="jornada-ubicacion__icono">
                <AuthIcon :name="estadoGps.icono" />
              </span>
            </button>

            <div class="jornada-ubicacion__info">
              <span class="jornada-ubicacion__titulo">{{ estadoGps.titulo }}</span>
              <span class="jornada-ubicacion__subtitulo">{{ estadoGps.subtitulo }}</span>
            </div>
          </div>

          <div v-if="gps?.latitud != null" class="jornada-ubicacion__coords" :class="{ 'jornada-ubicacion__coords--aviso': gps.estado_gps === 'GPS_IMPRECISO' }">
            <span class="jornada-ubicacion__coord"><b>Lat</b> {{ gps.latitud.toFixed(6) }}</span>
            <span class="jornada-ubicacion__coord-sep"></span>
            <span class="jornada-ubicacion__coord"><b>Lon</b> {{ gps.longitud.toFixed(6) }}</span>
          </div>

          <p v-if="gps?.permiso_denegado" class="jornada-modal__aviso-permiso">
            Activa el permiso de ubicación de este sitio en tu dispositivo y toca el círculo para reintentar.
          </p>
        </div>

        <div class="jornada-modal__reloj">
          <div class="jornada-modal__hora">{{ horaFormateada }}</div>
          <div class="jornada-modal__fecha">{{ fechaFormateada }}</div>
        </div>

        <label class="jornada-modal__campo-nota">
          <span>{{ textos.etiquetaNota }} <strong class="jornada-modal__requerido">*</strong></span>
          <textarea
            v-model="nota"
            class="jornada-modal__nota"
            :class="{ 'jornada-modal__nota--invalida': notaInvalida }"
            rows="3"
            :placeholder="textos.placeholderNota"
            :disabled="fase === FASE.CONFIRMANDO"
            @blur="notaTocada = true"
          ></textarea>
          <span v-if="notaInvalida" class="jornada-modal__nota-error">Este detalle es obligatorio.</span>
        </label>

        <div class="jornada-modal__botones">
          <button type="button" class="eca-btn eca-btn-secundario" :disabled="fase === FASE.CONFIRMANDO" @click="emit('cancelar')">
            Cancelar
          </button>
          <button
            type="button"
            class="eca-btn eca-btn-primary"
            :disabled="!puedeConfirmar || fase === FASE.CONFIRMANDO"
            @click="confirmar"
          >
            <span v-if="fase === FASE.CONFIRMANDO" class="jornada-modal__spin"></span>
            {{ fase === FASE.CONFIRMANDO ? textos.confirmando : textos.boton }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.jornada-modal__overlay {
  position: fixed;
  inset: 0;
  background: rgba(4, 28, 14, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 1rem;
}
.jornada-modal {
  width: 100%;
  max-width: 360px;
  background: #fff;
  border-radius: var(--eca-r-lg);
  box-shadow: 0 30px 60px rgba(2, 20, 10, 0.35);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.85rem;
  animation: jornada-modal-entrar 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes jornada-modal-entrar {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(12px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.jornada-modal__cabecera {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.jornada-modal__cabecera h2 {
  margin: 0;
  color: var(--eca-green-900);
  font-size: 1.15rem;
}
.jornada-modal__cerrar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: none;
  background: var(--eca-surface);
  color: var(--eca-ink-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.jornada-modal__cerrar svg {
  width: 16px;
  height: 16px;
}

/* Botón de ubicación circular tipo Apple — calcado a propósito de
   `.apple-location-btn` en pwasuper (mismos tamaños, gradientes, anillo
   de progreso y pulso de éxito), con una paleta propia por estado en vez
   de la de pwasuper porque aquí SÍ existe un estado intermedio real
   ("imprecisa": hubo lectura real de GPS pero fuera del umbral de buena
   precisión) que pwasuper no distingue visualmente. */
.jornada-ubicacion {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
}
.jornada-ubicacion__envoltura {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}
.jornada-ubicacion__boton {
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
.jornada-ubicacion__boton:disabled {
  cursor: default;
}
.jornada-ubicacion__boton:not(:disabled):hover {
  transform: scale(1.05);
}
.jornada-ubicacion__boton:not(:disabled):active {
  transform: scale(0.95);
}
.jornada-ubicacion__icono {
  display: flex;
  color: #fff;
  z-index: 2;
}
.jornada-ubicacion__icono svg {
  width: 1.8rem;
  height: 1.8rem;
}

/* Cargando: azul, con el anillo de progreso girando. */
.jornada-ubicacion__boton--cargando {
  background: linear-gradient(180deg, #5ac8fa 0%, #34aadc 100%);
  box-shadow: 0 6px 18px rgba(90, 200, 250, 0.4);
  cursor: wait;
}
/* Lista (CON_GPS): verde, con el pulso de éxito. */
.jornada-ubicacion__boton--lista {
  background: linear-gradient(180deg, #30d158 0%, #16a34a 100%);
  box-shadow: 0 6px 18px rgba(22, 163, 74, 0.4);
}
/* Imprecisa (GPS_IMPRECISO): ámbar — hubo lectura real, pero no basta. */
.jornada-ubicacion__boton--imprecisa {
  background: linear-gradient(180deg, #fbbf24 0%, #d97706 100%);
  box-shadow: 0 6px 18px rgba(217, 119, 6, 0.35);
}
/* Sin señal: gris — no hubo ninguna lectura real todavía. */
.jornada-ubicacion__boton--sin-senal {
  background: linear-gradient(180deg, #9ca3af 0%, #6b7280 100%);
  box-shadow: 0 4px 14px rgba(107, 114, 128, 0.3);
}

.jornada-ubicacion__anillo {
  position: absolute;
  inset: -5px;
  z-index: 1;
  animation: jornada-ubicacion-girar 1s linear infinite;
}
.jornada-ubicacion__anillo-svg {
  width: 100%;
  height: 100%;
}
.jornada-ubicacion__anillo-fondo {
  fill: none;
  stroke: rgba(255, 255, 255, 0.2);
  stroke-width: 4;
}
.jornada-ubicacion__anillo-progreso {
  fill: none;
  stroke: #fff;
  stroke-width: 4;
  stroke-linecap: round;
  stroke-dasharray: 70 213;
  transform-origin: center;
}
@keyframes jornada-ubicacion-girar {
  to {
    transform: rotate(360deg);
  }
}

.jornada-ubicacion__pulso {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(22, 163, 74, 0.3);
  animation: jornada-ubicacion-pulso 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  z-index: 0;
}
@keyframes jornada-ubicacion-pulso {
  0%, 100% {
    transform: scale(1);
    opacity: 0.6;
  }
  50% {
    transform: scale(1.2);
    opacity: 0;
  }
}

.jornada-ubicacion__info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
}
.jornada-ubicacion__titulo {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--eca-ink);
}
.jornada-ubicacion__subtitulo {
  font-size: 0.75rem;
  color: var(--eca-ink-soft);
}

.jornada-ubicacion__coords {
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
  animation: jornada-ubicacion-coords-entrar 0.3s ease both;
  max-width: 100%;
}
.jornada-ubicacion__coords--aviso {
  background: var(--eca-warn-bg);
  border-color: var(--eca-warn);
  color: var(--eca-warn);
}
.jornada-ubicacion__coord b {
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.62rem;
  margin-right: 0.2rem;
}
.jornada-ubicacion__coord-sep {
  width: 1px;
  height: 0.7rem;
  background: currentColor;
  opacity: 0.35;
}
@keyframes jornada-ubicacion-coords-entrar {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.jornada-modal__aviso-permiso {
  margin: -0.4rem 0 0;
  font-size: 0.78rem;
  color: var(--eca-ink-soft);
  text-align: center;
}

.jornada-modal__reloj {
  text-align: center;
  padding: 0.75rem 1rem;
  border-radius: var(--eca-r-md);
  background: var(--eca-surface);
  width: 100%;
}
.jornada-modal__hora {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--eca-green-900);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}
.jornada-modal__fecha {
  font-size: 0.8rem;
  color: var(--eca-ink-soft);
  text-transform: capitalize;
}

.jornada-modal__campo-nota {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  text-align: left;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--eca-ink-soft);
}
.jornada-modal__requerido {
  color: var(--eca-danger);
}
.jornada-modal__nota {
  width: 100%;
  resize: vertical;
  min-height: 4.5rem;
  padding: 0.65rem 0.8rem;
  border-radius: var(--eca-r-sm);
  border: 1.5px solid var(--eca-surface-border);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 400;
  color: var(--eca-ink);
  background: #fff;
}
.jornada-modal__nota:focus {
  outline: none;
  border-color: var(--eca-green-500);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.18);
}
.jornada-modal__nota--invalida {
  border-color: var(--eca-danger-border);
}
.jornada-modal__nota-error {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--eca-danger);
}

.jornada-modal__botones {
  display: flex;
  gap: 0.6rem;
  width: 100%;
}
.jornada-modal__botones .eca-btn {
  flex: 1;
}
.jornada-modal__spin {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: jornada-spin 0.7s linear infinite;
  display: inline-block;
  margin-right: 0.4rem;
}
@keyframes jornada-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
