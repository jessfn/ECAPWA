<!-- pwa-eca — pantalla "Jornada" (ECA-012). Rediseño pedido explícito:
     tarjetas grandes (como las de "inicio/salida" de pwasuper) lado a lado,
     altas verticalmente para ocupar el alto disponible de la pantalla, con
     un círculo de icono centrado; la acción todavía no disponible se ve en
     gris con candado y una franja "BLOQUEADO" abajo, igual que en las
     imágenes de referencia. "Terminar" queda bloqueada hasta que se
     registre el inicio, y viceversa una vez ya registrada. Cada acción abre
     `JornadaAccionModal` (ubicación + reloj en vivo + detalle obligatorio)
     antes de confirmar. -->
<script setup>
import { onMounted, ref } from 'vue'
import { useJornadaStore } from '../stores/jornada'
import BackButton from '../components/BackButton.vue'
import JornadaAccionModal from '../components/JornadaAccionModal.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'

const jornada = useJornadaStore()
const modalAbierto = ref(null) // null | 'inicio' | 'fin'

onMounted(() => {
  jornada.cargarHoy()
})

async function confirmarModal({ nota, gps }) {
  if (modalAbierto.value === 'inicio') {
    await jornada.iniciar(nota, gps)
  } else if (modalAbierto.value === 'fin') {
    await jornada.cerrar(nota, gps)
  }
  modalAbierto.value = null
}
</script>

<template>
  <main class="eca-contenido jornada-pantalla">
    <BackButton class="eca-entrar" />

    <div class="jornada-encabezado eca-entrar" style="--eca-delay: 0.05s">
      <h1 class="eca-titulo">Jornada de hoy</h1>
      <p class="eca-ayuda">Registra tu inicio y tu salida; cada uno pide tu ubicación y un detalle.</p>
      <p v-if="jornada.error" class="eca-alerta-error" role="alert">{{ jornada.error }}</p>
    </div>

    <div class="jornada-fila">
      <!-- Registro de inicio -->
      <button
        v-if="!jornada.actual"
        type="button"
        class="jornada-tarjeta jornada-tarjeta--activa jornada-tarjeta--inicio"
        :disabled="jornada.cargando"
        @click="modalAbierto = 'inicio'"
      >
        <span class="jornada-tarjeta__circulo">
          <AuthIcon name="login" />
        </span>
        <span class="jornada-tarjeta__titulo">Registro de Inicio</span>
        <span class="jornada-tarjeta__subtitulo">Inicia tu jornada</span>
      </button>
      <div v-else class="jornada-tarjeta jornada-tarjeta--hecha">
        <span class="jornada-tarjeta__circulo jornada-tarjeta__circulo--hecho">
          <AuthIcon name="check" />
        </span>
        <span class="jornada-tarjeta__titulo jornada-tarjeta__titulo--oscuro">Registro de Inicio</span>
        <span class="jornada-tarjeta__subtitulo jornada-tarjeta__subtitulo--oscuro">
          {{ new Date(jornada.actual.inicio_en).toLocaleTimeString('es-MX') }}
        </span>
        <span class="jornada-tarjeta__franja jornada-tarjeta__franja--hecha">REGISTRADO</span>
      </div>

      <!-- Registro de término -->
      <button
        v-if="jornada.abierta"
        type="button"
        class="jornada-tarjeta jornada-tarjeta--activa jornada-tarjeta--fin"
        :disabled="jornada.cargando"
        @click="modalAbierto = 'fin'"
      >
        <span class="jornada-tarjeta__circulo">
          <AuthIcon name="logout" />
        </span>
        <span class="jornada-tarjeta__titulo">Registro de Término</span>
        <span class="jornada-tarjeta__subtitulo">Marca tu salida</span>
      </button>
      <div v-else-if="jornada.actual" class="jornada-tarjeta jornada-tarjeta--hecha">
        <span class="jornada-tarjeta__circulo jornada-tarjeta__circulo--hecho">
          <AuthIcon name="check" />
        </span>
        <span class="jornada-tarjeta__titulo jornada-tarjeta__titulo--oscuro">Registro de Término</span>
        <span class="jornada-tarjeta__subtitulo jornada-tarjeta__subtitulo--oscuro">
          {{ new Date(jornada.actual.fin_en).toLocaleTimeString('es-MX') }}
        </span>
        <span class="jornada-tarjeta__franja jornada-tarjeta__franja--hecha">REGISTRADO</span>
      </div>
      <div v-else class="jornada-tarjeta jornada-tarjeta--bloqueada">
        <span class="jornada-tarjeta__circulo jornada-tarjeta__circulo--bloqueado">
          <AuthIcon name="lock" />
        </span>
        <span class="jornada-tarjeta__titulo jornada-tarjeta__titulo--oscuro">Registro de Término</span>
        <span class="jornada-tarjeta__subtitulo">Primero registra tu inicio</span>
        <span class="jornada-tarjeta__franja jornada-tarjeta__franja--bloqueada">BLOQUEADO</span>
      </div>
    </div>

    <JornadaAccionModal
      v-if="modalAbierto"
      :tipo="modalAbierto"
      @cancelar="modalAbierto = null"
      @confirmar="confirmarModal"
    />
  </main>
</template>

<style scoped>
.jornada-pantalla {
  display: flex;
  flex-direction: column;
}
.jornada-encabezado {
  margin-bottom: 1rem;
}
.jornada-encabezado .eca-titulo {
  margin-bottom: 0.3rem;
}

.jornada-fila {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.9rem;
  flex: 1;
  /* Alto acoplado a la pantalla donde se abra — pedido explícito: no un
     tamaño fijo, sino lo que quede disponible de viewport bajo el
     encabezado (aprox. header + BackButton + título/ayuda). */
  min-height: calc(100svh - 15.5rem);
}

.jornada-tarjeta {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.9rem;
  width: 100%;
  min-height: 20rem;
  padding: 1.5rem 1rem;
  border-radius: var(--eca-r-lg);
  border: none;
  cursor: default;
  text-align: center;
  overflow: hidden;
  box-shadow: var(--eca-shadow-card);
  font: inherit;
}

/* Tarjeta activa (clicable): degradado a color, como pwasuper. Azul para
   iniciar, rojo/anaranjado para terminar — mismo lenguaje visual que el
   resto de la app (verde=ok, dorado=logro, rojo=acción de salida). */
.jornada-tarjeta--activa {
  cursor: pointer;
  color: #fff;
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease;
}
.jornada-tarjeta--activa:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 16px 32px rgba(2, 20, 10, 0.18);
}
.jornada-tarjeta--activa:active:not(:disabled) {
  transform: scale(0.98);
}
.jornada-tarjeta--activa:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}
.jornada-tarjeta--inicio {
  background: linear-gradient(160deg, #3b82f6 0%, #1d4ed8 100%);
}
.jornada-tarjeta--fin {
  background: linear-gradient(160deg, #fb7185 0%, #dc2626 100%);
}

.jornada-tarjeta__circulo {
  width: 5.5rem;
  height: 5.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.22);
  flex-shrink: 0;
}
.jornada-tarjeta__circulo svg {
  width: 2.3rem;
  height: 2.3rem;
}
.jornada-tarjeta__circulo--bloqueado {
  background: var(--eca-surface);
  color: var(--eca-ink-faint);
}
.jornada-tarjeta__circulo--hecho {
  background: var(--eca-green-100);
  color: var(--eca-green-700);
}

.jornada-tarjeta__titulo {
  font-size: 1.05rem;
  font-weight: 800;
}
.jornada-tarjeta__titulo--oscuro {
  color: var(--eca-ink);
}
.jornada-tarjeta__subtitulo {
  font-size: 0.85rem;
  opacity: 0.92;
}
.jornada-tarjeta__subtitulo--oscuro {
  color: var(--eca-ink-soft);
  opacity: 1;
}

/* Tarjeta bloqueada / ya hecha: blanca, con franja inferior de ancho
   completo — pedido explícito, calcado de la imagen de referencia. */
.jornada-tarjeta--bloqueada,
.jornada-tarjeta--hecha {
  background: #fff;
  border: 1.5px solid var(--eca-surface-border);
  padding-bottom: 0;
}
.jornada-tarjeta__franja {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 0.85rem 0.5rem;
  font-size: 0.85rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: #fff;
}
.jornada-tarjeta__franja--bloqueada {
  background: #4b5563;
}
.jornada-tarjeta__franja--hecha {
  background: linear-gradient(100deg, #92400e 0%, #f59e0b 50%, #b45309 100%);
}

@media (max-width: 480px) {
  .jornada-fila {
    gap: 0.6rem;
  }
  .jornada-tarjeta {
    min-height: 17rem;
    padding: 1.1rem 0.75rem;
  }
  .jornada-tarjeta__circulo {
    width: 4.5rem;
    height: 4.5rem;
  }
  .jornada-tarjeta__circulo svg {
    width: 1.9rem;
    height: 1.9rem;
  }
  .jornada-tarjeta__titulo {
    font-size: 0.95rem;
  }
}
</style>
