<!-- pwa-eca — pantalla "Perfil" (ECA-011): datos del usuario y cambio de
     contraseña. Requiere red (llama al backend); sin conexión se deshabilita. -->
<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useConectividad } from '../services/conectividad'
import { api } from '../services/api'
import BackButton from '../components/BackButton.vue'

const auth = useAuthStore()
const { enLinea } = useConectividad()

const iniciales = computed(() => {
  const n = auth.usuario?.nombre?.[0] || ''
  const a = auth.usuario?.apellido_paterno?.[0] || ''
  return (n + a).toUpperCase() || 'TE'
})

const contrasenaActual = ref('')
const contrasenaNueva = ref('')
const guardando = ref(false)
const error = ref('')
const mensaje = ref('')

async function cambiarContrasena() {
  error.value = ''
  mensaje.value = ''
  guardando.value = true
  try {
    await api.post('/auth/password', {
      contrasena_actual: contrasenaActual.value,
      contrasena_nueva: contrasenaNueva.value,
    })
    contrasenaActual.value = ''
    contrasenaNueva.value = ''
    mensaje.value = 'Contraseña actualizada.'
  } catch (err) {
    error.value = err.response?.data?.error?.message || 'No se pudo cambiar la contraseña.'
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <div class="eca-card perfil-card eca-entrar" style="--eca-delay: 0.06s">
      <div class="perfil__cabecera">
        <span class="perfil__avatar">{{ iniciales }}</span>
        <div>
          <h1 class="eca-titulo perfil__nombre">{{ auth.usuario?.nombre }} {{ auth.usuario?.apellido_paterno }}</h1>
          <p class="eca-ayuda">{{ auth.usuario?.correo }}</p>
        </div>
      </div>
    </div>

    <div class="eca-card perfil-card eca-entrar" style="--eca-delay: 0.12s">
      <h2 class="eca-titulo">Cambiar contraseña</h2>
      <p v-if="!enLinea" class="eca-alerta-aviso" role="status">
        Sin conexión: no puedes cambiar la contraseña ahora.
      </p>

      <form class="eca-form" @submit.prevent="cambiarContrasena">
        <label>
          Contraseña actual
          <input v-model="contrasenaActual" type="password" required :disabled="!enLinea" />
        </label>
        <label>
          Contraseña nueva
          <input v-model="contrasenaNueva" type="password" required :disabled="!enLinea" />
        </label>

        <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>
        <p v-if="mensaje" class="eca-alerta-ok">{{ mensaje }}</p>

        <button type="submit" class="eca-btn eca-btn-primary" :disabled="guardando || !enLinea">
          {{ guardando ? 'Guardando…' : 'Cambiar contraseña' }}
        </button>
      </form>
    </div>
  </main>
</template>

<style scoped>
.perfil-card + .perfil-card {
  margin-top: 1rem;
}
.perfil__cabecera {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.perfil__avatar {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  color: #fff;
  background: linear-gradient(145deg, var(--eca-green-400) 0%, var(--eca-green-600) 100%);
  box-shadow: 0 6px 16px rgba(21, 128, 61, 0.3);
}
.perfil__nombre {
  margin-bottom: 0.15rem;
}
</style>
