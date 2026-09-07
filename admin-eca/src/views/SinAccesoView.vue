<!-- admin-eca — pantalla de respaldo para una cuenta USUARIO sin ningún
     `vista.*` activo. No debería pasar en el flujo normal (crear/editar
     usuario siempre permite elegir vistas), pero sin esta vista el router
     no tendría a dónde mandarla y volveríamos al bucle de redirección. -->
<script setup>
import { useAuthStore } from '../stores/auth'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()
</script>

<template>
  <section class="sin-acceso">
    <span class="sin-acceso__icono"><AuthIcon name="shield" /></span>
    <h1>Sin vistas asignadas</h1>
    <p>Tu cuenta todavía no tiene acceso a ninguna sección del panel. Pide a un administrador que te asigne al menos un permiso desde "Permisos administrativos".</p>
    <button type="button" class="eca-btn eca-btn-secundario" @click="auth.logout()">Cerrar sesión</button>
  </section>
</template>

<style scoped>
.sin-acceso {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.9rem;
  max-width: 420px;
  margin: 4rem auto;
  padding: 2rem;
}
.sin-acceso__icono {
  width: 3.2rem;
  height: 3.2rem;
  border-radius: 50%;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #d97706;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sin-acceso__icono svg {
  width: 1.4rem;
  height: 1.4rem;
}
.sin-acceso h1 {
  margin: 0;
  font-size: 1.15rem;
}
.sin-acceso p {
  margin: 0;
  color: var(--eca-ink-soft);
  font-size: 0.9rem;
  line-height: 1.5;
}
</style>
