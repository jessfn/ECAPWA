<!-- admin-eca — layout del panel autenticado. El sidebar vive en
     `components/Sidebar.vue` (paridad visual con `admin-pwa`); este layout
     solo pone el fondo y el margen del contenido, igual que
     `.apple-main-content`/`body` en admin-pwa. -->
<script setup>
import Sidebar from '../components/Sidebar.vue'
</script>

<template>
  <div class="layout">
    <Sidebar />
    <main class="layout__contenido">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  min-height: 100dvh;
  background-color: #f5f5f5;
}
.layout__contenido {
  margin-left: min(220px, 18vw);
  min-height: 100vh;
  min-height: 100dvh;
  /* Mismo espaciado que `.apple-main-content` de admin-pwa: poco margen
     arriba/lados y nada abajo — la vista es la que decide su propio
     padding interno (dentro de `.eca-page-header`/`.eca-panel-fusionado`).
     Antes eran 2rem parejos en los cuatro lados, muy separado del borde
     de la ventana comparado con el original. */
  padding: 0.6rem 1rem 1rem;
  box-sizing: border-box;
}
@media (max-width: 768px) {
  .layout__contenido {
    /* El sidebar se colapsa a un riel de 60px de solo iconos en este
       breakpoint (ver Sidebar.vue) — el margen debe coincidir. */
    margin-left: 60px;
    padding: 0.5rem 0.6rem 1rem;
  }
}
</style>
