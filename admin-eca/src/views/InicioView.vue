<script setup>
// admin-eca — pantalla de inicio.
import { useAuthStore } from '../stores/auth'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()
</script>

<template>
  <section>
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="home" /></span>
      <div class="eca-page-header__texto">
        <h1>Inicio</h1>
        <p>Panel de administración de ECA.</p>
      </div>
    </div>
    <div class="eca-card eca-panel-fusionado">
      <p v-if="auth.usuario" class="eca-ayuda">
        Sesión iniciada como {{ auth.usuario.nombre }} {{ auth.usuario.apellido_paterno }}.
      </p>
    </div>
  </section>
</template>
