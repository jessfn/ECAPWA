<!-- pwa-eca — modal de confirmación para iniciar/terminar jornada.
     Pedido explícito: al tocar "Iniciar jornada" (o "Terminar jornada") se
     abre esta ficha, se pide la ubicación con una animación tipo radar
     (el GPS del dispositivo funciona sin internet — `services/gps.js` ya
     usa `navigator.geolocation`, nunca la red), se muestra fecha/hora en
     vivo, y solo entonces aparece el botón para confirmar. -->
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

let temporizadorReloj = null

const textos = computed(() =>
  props.tipo === 'inicio'
    ? { titulo: 'Iniciar jornada', boton: 'Confirmar inicio', confirmando: 'Iniciando…' }
    : { titulo: 'Terminar jornada', boton: 'Confirmar salida', confirmando: 'Terminando…' },
)

const estadoGps = computed(() => {
  if (!gps.value) return null
  const mapa = {
    CON_GPS: { icono: 'check', clase: 'jornada-modal__ubicacion--ok', texto: 'Ubicación obtenida' },
    GPS_IMPRECISO: { icono: 'map-pin', clase: 'jornada-modal__ubicacion--aviso', texto: 'Ubicación aproximada' },
    SIN_GPS: { icono: 'wifi-off', clase: 'jornada-modal__ubicacion--sin', texto: 'Sin señal de ubicación' },
  }
  return mapa[gps.value.estado_gps] || mapa.SIN_GPS
})

const fechaFormateada = computed(() =>
  ahora.value.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
)
const horaFormateada = computed(() => ahora.value.toLocaleTimeString('es-MX'))

async function buscarUbicacion() {
  fase.value = FASE.BUSCANDO
  gps.value = await capturarGps({ intentos: 2, timeoutMs: 5000 })
  fase.value = FASE.LISTO
}

async function confirmar() {
  fase.value = FASE.CONFIRMANDO
  // `gps` es un `ref()`: un objeto asignado a un ref se vuelve reactivo
  // (Proxy) automáticamente. IndexedDB no puede clonar un Proxy
  // (`DataCloneError` al hacer `put`) — se emite una copia plana.
  await emit('confirmar', gps.value ? { ...gps.value } : null)
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

        <div class="jornada-modal__radar">
          <span class="jornada-modal__onda" :class="{ 'jornada-modal__onda--activa': fase === FASE.BUSCANDO }"></span>
          <span class="jornada-modal__onda jornada-modal__onda--2" :class="{ 'jornada-modal__onda--activa': fase === FASE.BUSCANDO }"></span>
          <span class="jornada-modal__pin" :class="{ 'jornada-modal__pin--listo': fase !== FASE.BUSCANDO }">
            <AuthIcon name="map-pin" />
          </span>
        </div>

        <p v-if="fase === FASE.BUSCANDO" class="jornada-modal__estado">Obteniendo tu ubicación…</p>
        <div v-else class="jornada-modal__ubicacion" :class="estadoGps.clase">
          <AuthIcon :name="estadoGps.icono" />
          <span>{{ estadoGps.texto }}</span>
          <span v-if="gps?.precision_gps_m" class="jornada-modal__precision">
            ±{{ Math.round(gps.precision_gps_m) }} m
          </span>
        </div>

        <div class="jornada-modal__reloj">
          <div class="jornada-modal__hora">{{ horaFormateada }}</div>
          <div class="jornada-modal__fecha">{{ fechaFormateada }}</div>
        </div>

        <div class="jornada-modal__botones">
          <button type="button" class="eca-btn eca-btn-secundario" :disabled="fase === FASE.CONFIRMANDO" @click="emit('cancelar')">
            Cancelar
          </button>
          <button
            type="button"
            class="eca-btn eca-btn-primary"
            :disabled="fase === FASE.BUSCANDO || fase === FASE.CONFIRMANDO"
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

.jornada-modal__radar {
  width: 7rem;
  height: 7rem;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin: 0.25rem 0;
}
.jornada-modal__onda {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid var(--eca-green-400);
  opacity: 0;
}
.jornada-modal__onda--activa {
  animation: jornada-radar-onda 1.8s ease-out infinite;
}
.jornada-modal__onda--2.jornada-modal__onda--activa {
  animation-delay: 0.6s;
}
@keyframes jornada-radar-onda {
  0% {
    transform: scale(0.5);
    opacity: 0.7;
  }
  100% {
    transform: scale(1.35);
    opacity: 0;
  }
}
.jornada-modal__pin {
  width: 3.75rem;
  height: 3.75rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, var(--eca-green-400) 0%, var(--eca-green-600) 100%);
  color: #fff;
  box-shadow: 0 8px 20px rgba(21, 128, 61, 0.35);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 1;
}
.jornada-modal__pin svg {
  width: 1.9rem;
  height: 1.9rem;
}
.jornada-modal__pin--listo {
  transform: scale(1.08);
}

.jornada-modal__estado {
  margin: 0;
  color: var(--eca-ink-soft);
  font-size: 0.9rem;
}
.jornada-modal__ubicacion {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  background: var(--eca-green-100);
  color: var(--eca-green-800);
}
.jornada-modal__ubicacion svg {
  width: 15px;
  height: 15px;
}
.jornada-modal__ubicacion--aviso {
  background: var(--eca-warn-bg);
  color: var(--eca-warn);
}
.jornada-modal__ubicacion--sin {
  background: var(--eca-surface);
  color: var(--eca-ink-soft);
}
.jornada-modal__precision {
  opacity: 0.75;
  font-weight: 400;
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
