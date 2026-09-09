<!-- admin-eca — vista unificada "Modificaciones" (pedido explícito): consolida
     las 4 pantallas de configuración —ECA, Ámbitos, Asignaciones y Catálogos—
     en una sola, con pestañas por módulo. Cada pestaña reutiliza su vista
     original COMO COMPONENTE (`:embebido="true"`, que oculta su header verde
     propio para no duplicarlo con el de aquí); toda la lógica de datos de
     cada módulo vive intacta en su componente, no se reescribió nada. Se usa
     `<KeepAlive>` para no recargar los datos de una pestaña cada vez que se
     cambia entre ellas. -->
<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import EcasView from './EcasView.vue'
import AmbitosView from './AmbitosView.vue'
import AsignacionesView from './AsignacionesView.vue'
import CatalogosView from './CatalogosView.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'

const route = useRoute()

const PESTANAS = [
  { clave: 'ecas', etiqueta: 'ECA', icono: 'school', componente: EcasView },
  { clave: 'ambitos', etiqueta: 'Ámbitos', icono: 'shield', componente: AmbitosView },
  { clave: 'asignaciones', etiqueta: 'Asignaciones', icono: 'check-circle', componente: AsignacionesView },
  { clave: 'catalogos', etiqueta: 'Catálogos', icono: 'book', componente: CatalogosView },
]

// Permite abrir directo una pestaña con `?tab=ecas` (p. ej. al volver de la
// pantalla "Importar ECA"). Si el valor no es válido, cae en la primera.
const claveInicial = PESTANAS.some((p) => p.clave === route.query.tab) ? route.query.tab : 'ecas'
const activa = ref(claveInicial)

const componenteActivo = computed(() => PESTANAS.find((p) => p.clave === activa.value)?.componente)
</script>

<template>
  <section class="modificaciones-vista">
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="edit" /></span>
      <div class="eca-page-header__texto">
        <h1>Modificaciones</h1>
        <p>ECA, ámbitos, asignaciones y catálogos — todo en un solo lugar.</p>
      </div>
    </div>

    <nav class="modificaciones__tabs" role="tablist">
      <button
        v-for="p in PESTANAS"
        :key="p.clave"
        type="button"
        role="tab"
        class="modificaciones__tab"
        :class="{ 'modificaciones__tab--activa': activa === p.clave }"
        @click="activa = p.clave"
      >
        <AuthIcon :name="p.icono" /> {{ p.etiqueta }}
      </button>
    </nav>

    <div class="modificaciones__contenido">
      <KeepAlive>
        <component :is="componenteActivo" :embebido="true" />
      </KeepAlive>
    </div>
  </section>
</template>

<style scoped>
/* Barra de pestañas tipo segmentado — mismo lenguaje visual que las tabs
   de Historial/Catálogos, alineada con el ancho del contenido. */
.modificaciones__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0.75rem 1rem 0.25rem;
  padding: 0.35rem;
  background: var(--eca-surface);
  border-radius: 999px;
}
.modificaciones__tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  flex: 1 1 0;
  min-width: max-content;
  padding: 0.55rem 0.9rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--eca-ink-soft);
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}
.modificaciones__tab svg {
  width: 0.95rem;
  height: 0.95rem;
}
.modificaciones__tab:hover {
  color: var(--eca-ink);
}
.modificaciones__tab--activa {
  background: #fff;
  color: var(--eca-green-700);
  box-shadow: 0 2px 8px rgba(2, 20, 10, 0.12);
}
@media (max-width: 640px) {
  .modificaciones__tab {
    flex: 1 1 40%;
  }
}
</style>
