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
  background-color: #f5f5f5;
}
.layout__contenido {
  margin-left: min(220px, 18vw);
  min-height: 100vh;
  padding: 2rem;
  box-sizing: border-box;
}
@media (max-width: 900px) {
  .layout__contenido {
    margin-left: 200px;
    padding: 1.25rem;
  }
}
</style>
