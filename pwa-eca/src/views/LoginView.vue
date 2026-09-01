<!-- pwa-eca — pantalla de login (ECA-011 + ECA-020: rediseño con paridad
     visual a `pwasuper`). Requiere red: es el único punto donde SÍ es
     obligatorio estar en línea (primer ingreso / bootstrap). -->
<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useConectividad } from '../services/conectividad'
import AuthLayout from '../components/auth/AuthLayout.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { enLinea } = useConectividad()

const correo = ref('')
const contrasena = ref('')
const mostrarContrasena = ref(false)
const cargando = ref(false)
const error = ref('')
const shake = ref(false)

function fallar(mensaje) {
  error.value = mensaje
  shake.value = true
  setTimeout(() => {
    shake.value = false
  }, 600)
}

async function enviar() {
  if (!enLinea.value) {
    fallar('Sin conexión a internet. El primer ingreso requiere red.')
    return
  }
  error.value = ''
  cargando.value = true
  try {
    await auth.login(correo.value, contrasena.value)
    router.push(route.query.redirigir || { name: 'inicio' })
  } catch (err) {
    fallar(err.response?.data?.error?.message || 'No se pudo iniciar sesión. Intenta de nuevo.')
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="login-pantalla">
    <AuthLayout>
      <div class="au-card-head">
        <h1>¡Bienvenido de vuelta!</h1>
        <p>Ingresa tus credenciales para continuar</p>
      </div>

      <Transition name="au-fade">
        <div v-if="error" class="au-alert" role="alert">
          <AuthIcon :name="!enLinea ? 'wifi-off' : 'alert'" />
          <span>{{ error }}</span>
        </div>
      </Transition>

      <form class="au-form" novalidate @submit.prevent="enviar">
        <div class="au-field">
          <label for="correo">Correo electrónico</label>
          <div class="au-input" :class="{ 'is-error': shake }">
            <span class="au-ico"><AuthIcon name="mail" /></span>
            <input
              id="correo"
              v-model.trim="correo"
              type="email"
              inputmode="email"
              autocomplete="username"
              placeholder="nombre@ejemplo.com"
              :disabled="cargando"
              required
            />
          </div>
        </div>

        <div class="au-field">
          <label for="contrasena">Contraseña</label>
          <div class="au-input au-has-btn" :class="{ 'is-error': shake }">
            <span class="au-ico"><AuthIcon name="lock" /></span>
            <input
              id="contrasena"
              v-model="contrasena"
              :type="mostrarContrasena ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="Tu contraseña"
              :disabled="cargando"
              required
            />
            <button
              type="button"
              class="au-input-btn"
              :disabled="cargando"
              :aria-label="mostrarContrasena ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              tabindex="-1"
              @click="mostrarContrasena = !mostrarContrasena"
            >
              <AuthIcon :name="mostrarContrasena ? 'eye-off' : 'eye'" />
            </button>
          </div>
        </div>

        <button type="submit" class="au-btn au-btn-primary" :disabled="cargando">
          <span v-if="cargando" class="au-spin"></span>
          <span>{{ cargando ? 'Verificando…' : 'Iniciar sesión' }}</span>
          <AuthIcon v-if="!cargando" name="arrow-right" class="au-btn-arrow" />
        </button>
      </form>

      <div class="au-links">
        <p>¿Aún no tienes cuenta? <router-link to="/registro">Solicitar acceso</router-link></p>
      </div>

      <p class="au-copy card-copy">© 2026 ECA · Escuelas de Campo</p>
    </AuthLayout>
  </div>
</template>

<style scoped>
@media (min-width: 1000px) { .card-copy { display: none; } }
</style>
