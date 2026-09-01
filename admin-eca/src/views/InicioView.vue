<script setup>
// admin-eca — pantalla de inicio.
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
</script>

<template>
  <section class="eca-card">
    <h1 class="eca-titulo">Inicio</h1>
    <p v-if="auth.usuario" class="eca-ayuda">
      Sesión iniciada como {{ auth.usuario.nombre }} {{ auth.usuario.apellido_paterno }}.
    </p>
  </section>
</template>
