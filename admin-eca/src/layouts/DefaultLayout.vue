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
  /* Sin padding arriba ni a los lados: el header verde (`.eca-page-header`)
     va pegado al borde superior y de lado a lado (pedido explícito, estilo
     "barra de app"). El contenido bajo el header trae su propio margen
     lateral (`--eca-gutter`), así no queda pegado a los bordes. */
  --eca-gutter: 1rem;
  padding: 0 0 1rem;
  box-sizing: border-box;
}
@media (max-width: 768px) {
  .layout__contenido {
    /* El sidebar se colapsa a un riel de 60px de solo iconos en este
       breakpoint (ver Sidebar.vue) — el margen debe coincidir. */
    margin-left: 60px;
    --eca-gutter: 0.6rem;
  }
}
</style>
