<!-- admin-eca — pantalla de login (ECA-005 + ECA-020: rediseño con paridad
     visual a `admin-pwa`, que a su vez comparte el mismo sistema `au-` que
     `pwasuper`). -->
<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AuthLayout from '../components/auth/AuthLayout.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

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
    <AuthLayout
      badge="Panel administrativo"
      desc="Administra Escuelas de Campo, técnicos, catálogos y actividades registradas en el sistema."
      :features="['Gestión de técnicos y ECA', 'Catálogos configurables', 'Historial de actividades']"
    >
      <div class="au-card-head">
        <h1>Panel de Administración</h1>
        <p>Ingresa tus credenciales para continuar</p>
      </div>

      <Transition name="au-fade">
        <div v-if="error" class="au-alert" role="alert">
          <AuthIcon name="alert" />
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
              tabindex="-1"
              :disabled="cargando"
              :aria-label="mostrarContrasena ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              @click="mostrarContrasena = !mostrarContrasena"
            >
              <AuthIcon :name="mostrarContrasena ? 'eye-off' : 'eye'" />
            </button>
          </div>
        </div>

        <button type="submit" class="au-btn au-btn-primary submit" :disabled="cargando">
          <span v-if="cargando" class="au-spin"></span>
          <span>{{ cargando ? 'Verificando…' : 'Iniciar sesión' }}</span>
          <AuthIcon v-if="!cargando" name="arrow-right" class="au-btn-arrow" />
        </button>
      </form>

      <p class="au-copy card-copy">© 2026 ECA · Panel de Administración</p>
    </AuthLayout>
  </div>
</template>

<style scoped>
.submit { margin-top: 4px; }
@media (min-width: 1000px) { .card-copy { display: none; } }
</style>
