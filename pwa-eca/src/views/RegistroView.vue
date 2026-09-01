<!-- pwa-eca — pantalla "Registro" (ECA-020).
     ECA no tiene auto-registro de cuentas (las crea el administrador desde
     el panel, ver ECA-004) — esta pantalla, con la misma identidad visual
     que el login, deja una solicitud de acceso (`POST /solicitudes-acceso`,
     público, sin crear ningún usuario) para que el administrador la revise
     y dé de alta la cuenta él mismo. -->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../services/api'
import AuthLayout from '../components/auth/AuthLayout.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'

const router = useRouter()

const nombre = ref('')
const correo = ref('')
const telefono = ref('')
const notas = ref('')
const cargando = ref(false)
const error = ref('')
const enviado = ref(false)

async function enviar() {
  error.value = ''
  cargando.value = true
  try {
    await api.post('/solicitudes-acceso', {
      nombre: nombre.value,
      correo: correo.value,
      telefono: telefono.value || null,
      notas: notas.value || null,
    })
    enviado.value = true
  } catch (err) {
    error.value =
      err.response?.data?.error?.message || 'No se pudo enviar la solicitud. Intenta de nuevo.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="registro-pantalla">
    <AuthLayout
      wide
      badge="Alta gestionada por tu administrador"
      desc="En ECA las cuentas las crea el administrador de tu institución. Deja tus datos y te contactará para darte de alta."
      :features="['Revisión por el administrador', 'Sin datos de pago', 'Respuesta por correo o teléfono']"
    >
      <template v-if="!enviado">
        <div class="au-card-head">
          <h1>Solicitar acceso</h1>
          <p>Comparte tus datos y el administrador creará tu cuenta</p>
        </div>

        <Transition name="au-fade">
          <div v-if="error" class="au-alert" role="alert">
            <AuthIcon name="alert" />
            <span>{{ error }}</span>
          </div>
        </Transition>

        <form class="au-form" novalidate @submit.prevent="enviar">
          <div class="au-field">
            <label for="nombre">Nombre completo<span class="au-req">*</span></label>
            <div class="au-input">
              <span class="au-ico"><AuthIcon name="user" /></span>
              <input
                id="nombre"
                v-model.trim="nombre"
                type="text"
                autocomplete="name"
                placeholder="Tu nombre completo"
                :disabled="cargando"
                required
              />
            </div>
          </div>

          <div class="au-field">
            <label for="correo-registro">Correo electrónico<span class="au-req">*</span></label>
            <div class="au-input">
              <span class="au-ico"><AuthIcon name="mail" /></span>
              <input
                id="correo-registro"
                v-model.trim="correo"
                type="email"
                inputmode="email"
                autocomplete="email"
                placeholder="nombre@ejemplo.com"
                :disabled="cargando"
                required
              />
            </div>
          </div>

          <div class="au-field">
            <label for="telefono">Teléfono (opcional)</label>
            <div class="au-input">
              <span class="au-ico"><AuthIcon name="phone" /></span>
              <input
                id="telefono"
                v-model.trim="telefono"
                type="tel"
                inputmode="tel"
                autocomplete="tel"
                placeholder="10 dígitos"
                :disabled="cargando"
              />
            </div>
          </div>

          <div class="au-field">
            <label for="notas">Municipio o ECA donde trabajas (opcional)</label>
            <div class="au-input">
              <span class="au-ico"><AuthIcon name="map-pin" /></span>
              <textarea
                id="notas"
                v-model.trim="notas"
                rows="2"
                placeholder="Ayuda al administrador a ubicar tu solicitud"
                :disabled="cargando"
              />
            </div>
          </div>

          <button type="submit" class="au-btn au-btn-primary" :disabled="cargando">
            <span v-if="cargando" class="au-spin"></span>
            <span>{{ cargando ? 'Enviando…' : 'Enviar solicitud' }}</span>
            <AuthIcon v-if="!cargando" name="arrow-right" class="au-btn-arrow" />
          </button>
        </form>
      </template>

      <template v-else>
        <div class="au-card-head">
          <h1>Solicitud enviada</h1>
          <p>El administrador la revisará y te contactará</p>
        </div>

        <div class="au-alert is-ok" role="status">
          <AuthIcon name="check" />
          <span>Recibimos tus datos. En cuanto el administrador cree tu cuenta, podrás iniciar sesión aquí mismo.</span>
        </div>

        <button type="button" class="au-btn au-btn-ghost" @click="router.push({ name: 'login' })">
          <AuthIcon name="arrow-left" />
          <span>Volver al inicio de sesión</span>
        </button>
      </template>

      <div class="au-links">
        <p>¿Ya tienes cuenta? <router-link to="/login">Iniciar sesión</router-link></p>
      </div>
    </AuthLayout>
  </div>
</template>
