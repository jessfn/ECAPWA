<!-- pwa-eca — modal genérico de aviso (bloqueo o confirmación de éxito).
     Pedido explícito: cuando algo está bloqueado (p. ej. "Nueva actividad"
     sin jornada abierta) o cuando se completa una acción importante
     (iniciar/cerrar jornada, guardar actividad), debe aparecer un modal
     moderno con el fondo desvanecido explicando qué pasó — no solo un
     texto plano que a veces ni se alcanza a leer. -->
<script setup>
import AuthIcon from './auth/AuthIcon.vue'

const props = defineProps({
  tipo: { type: String, default: 'bloqueo' }, // 'bloqueo' | 'exito'
  titulo: { type: String, required: true },
  mensaje: { type: String, required: true },
  textoBoton: { type: String, default: 'Entendido' },
})
const emit = defineEmits(['cerrar'])
</script>

<template>
  <Teleport to="body">
    <div class="aviso-modal__overlay" @click.self="emit('cerrar')">
      <div class="aviso-modal" :class="`aviso-modal--${tipo}`">
        <span class="aviso-modal__icono">
          <AuthIcon :name="tipo === 'exito' ? 'check' : 'lock'" />
        </span>
        <h2 class="aviso-modal__titulo">{{ titulo }}</h2>
        <p class="aviso-modal__mensaje">{{ mensaje }}</p>
        <button type="button" class="eca-btn eca-btn-primary aviso-modal__boton" @click="emit('cerrar')">
          {{ textoBoton }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.aviso-modal__overlay {
  position: fixed;
  inset: 0;
  background: rgba(4, 28, 14, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
  padding: 1rem;
}
.aviso-modal {
  width: 100%;
  max-width: 340px;
  background: #fff;
  border-radius: var(--eca-r-lg);
  box-shadow: 0 30px 60px rgba(2, 20, 10, 0.35);
  padding: 1.75rem 1.5rem 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.6rem;
  animation: aviso-modal-entrar 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes aviso-modal-entrar {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(12px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.aviso-modal__icono {
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.3rem;
}
.aviso-modal__icono svg {
  width: 1.7rem;
  height: 1.7rem;
}
.aviso-modal--bloqueo .aviso-modal__icono {
  background: var(--eca-warn-bg);
  color: var(--eca-warn);
}
.aviso-modal--exito .aviso-modal__icono {
  background: var(--eca-green-100);
  color: var(--eca-green-700);
}
.aviso-modal__titulo {
  margin: 0;
  font-size: 1.1rem;
  color: var(--eca-green-900);
}
.aviso-modal__mensaje {
  margin: 0;
  font-size: 0.9rem;
  color: var(--eca-ink-soft);
  line-height: 1.45;
}
.aviso-modal__boton {
  width: 100%;
  margin-top: 0.5rem;
}
</style>
