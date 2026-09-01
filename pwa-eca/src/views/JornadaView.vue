<!-- pwa-eca — pantalla "Jornada" (ECA-012): "Iniciar jornada" y "Terminar
     jornada" van en fila, lado a lado; "Terminar" queda bloqueado hasta que
     se registre el inicio. Cada acción abre `JornadaAccionModal` (animación
     de ubicación + reloj en vivo) antes de confirmar. -->
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

async function confirmarModal(gps) {
  if (modalAbierto.value === 'inicio') {
    await jornada.iniciar(gps)
  } else if (modalAbierto.value === 'fin') {
    await jornada.cerrar(gps)
  }
  modalAbierto.value = null
}
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <div class="eca-card eca-entrar" style="--eca-delay: 0.06s">
      <h1 class="eca-titulo">Jornada de hoy</h1>
      <p class="eca-ayuda">Registra tu inicio y tu salida; cada uno pide tu ubicación al momento.</p>

      <p v-if="jornada.error" class="eca-alerta-error" role="alert">{{ jornada.error }}</p>

      <template v-if="jornada.abierta">
        <p class="eca-alerta-ok jornada-estado">
          <AuthIcon name="check" />
          Jornada abierta desde {{ new Date(jornada.actual.inicio_en).toLocaleTimeString('es-MX') }}
        </p>
      </template>
      <template v-else-if="jornada.actual">
        <p class="eca-ayuda jornada-estado">
          Jornada ya cerrada hoy ({{ new Date(jornada.actual.fin_en).toLocaleTimeString('es-MX') }}).
        </p>
      </template>
      <template v-else>
        <p class="eca-ayuda jornada-estado">Aún no inicias tu jornada de hoy.</p>
      </template>

      <div class="jornada-fila">
        <button
          type="button"
          class="jornada-accion jornada-accion--inicio"
          :class="{ 'jornada-accion--hecho': jornada.actual }"
          :disabled="Boolean(jornada.actual) || jornada.cargando"
          @click="modalAbierto = 'inicio'"
        >
          <span class="jornada-accion__icono">
            <AuthIcon :name="jornada.actual ? 'check' : 'calendar'" />
          </span>
          <span class="jornada-accion__texto">
            <strong>Iniciar jornada</strong>
            <span>{{ jornada.actual ? 'Registrado' : 'Marca tu llegada' }}</span>
          </span>
        </button>

        <button
          type="button"
          class="jornada-accion jornada-accion--fin"
          :class="{ 'jornada-accion--hecho': jornada.actual && !jornada.abierta }"
          :disabled="!jornada.abierta || jornada.cargando"
          @click="modalAbierto = 'fin'"
        >
          <span class="jornada-accion__icono">
            <AuthIcon :name="jornada.actual && !jornada.abierta ? 'check' : jornada.abierta ? 'logout' : 'lock'" />
          </span>
          <span class="jornada-accion__texto">
            <strong>Terminar jornada</strong>
            <span v-if="!jornada.abierta && !(jornada.actual && !jornada.abierta)">Inicia primero</span>
            <span v-else-if="jornada.actual && !jornada.abierta">Registrado</span>
            <span v-else>Marca tu salida</span>
          </span>
        </button>
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
.jornada-estado {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: fit-content;
}
.jornada-estado svg {
  width: 15px;
  height: 15px;
}

.jornada-fila {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-top: 1.1rem;
}
.jornada-accion {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.1rem 0.75rem;
  border-radius: var(--eca-r-md);
  border: 1.5px solid var(--eca-surface-border);
  background: #fff;
  cursor: pointer;
  transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.15s ease, border-color 0.15s ease;
  text-align: center;
}
.jornada-accion:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(2, 20, 10, 0.1);
}
.jornada-accion:not(:disabled):active {
  transform: scale(0.97);
}
.jornada-accion:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.jornada-accion__icono {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--eca-surface);
  color: var(--eca-ink-faint);
  transition: background 0.15s ease, color 0.15s ease;
}
.jornada-accion__icono svg {
  width: 1.3rem;
  height: 1.3rem;
}
.jornada-accion--inicio:not(:disabled) .jornada-accion__icono {
  background: var(--eca-green-100);
  color: var(--eca-green-700);
}
.jornada-accion--fin:not(:disabled) .jornada-accion__icono {
  background: #fee2e2;
  color: #dc2626;
}
.jornada-accion--hecho .jornada-accion__icono {
  background: var(--eca-green-600);
  color: #fff;
}
.jornada-accion--hecho {
  border-color: var(--eca-green-300);
  opacity: 1;
}
.jornada-accion__texto {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.jornada-accion__texto strong {
  font-size: 0.92rem;
  color: var(--eca-ink);
}
.jornada-accion__texto span {
  font-size: 0.75rem;
  color: var(--eca-ink-faint);
}
</style>
