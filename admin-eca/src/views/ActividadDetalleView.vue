<!-- admin-eca — pantalla "Detalle de actividad" (ECA-019): datos completos +
     galería de evidencias con descarga autenticada (nunca estático público). -->
<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { obtenerActividad, descargarEvidencia, urlVistaPreviaEvidencia } from '../services/actividadesService'

const route = useRoute()
const actividad = ref(null)
const cargando = ref(true)
const error = ref('')
const vistasPrevias = ref({}) // evidenciaId -> object URL

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    actividad.value = await obtenerActividad(route.params.uuid)
    for (const evidencia of actividad.value.evidencias) {
      urlVistaPreviaEvidencia(evidencia.id)
        .then((url) => {
          vistasPrevias.value = { ...vistasPrevias.value, [evidencia.id]: url }
        })
        .catch(() => {})
    }
  } catch {
    error.value = 'No se pudo cargar la actividad (o no tienes permiso para verla).'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

onBeforeUnmount(() => {
  for (const url of Object.values(vistasPrevias.value)) URL.revokeObjectURL(url)
})
</script>

<template>
  <section class="eca-card">
    <p><RouterLink :to="{ name: 'actividades' }">← Volver</RouterLink></p>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>
    <p v-if="cargando" class="eca-ayuda">Cargando…</p>

    <template v-else-if="actividad">
      <h1 class="eca-titulo">Actividad {{ actividad.uuid }}</h1>

      <dl class="detalle__datos">
        <dt>Fecha</dt>
        <dd>{{ new Date(actividad.fecha_hora).toLocaleString() }}</dd>
        <dt>Técnico</dt>
        <dd>{{ actividad.usuario_id }}</dd>
        <dt>ECA</dt>
        <dd>{{ actividad.eca_id || '—' }}</dd>
        <dt>Descripción</dt>
        <dd>{{ actividad.descripcion }}</dd>
        <dt>Resultado</dt>
        <dd>{{ actividad.resultado || '—' }}</dd>
        <dt>GPS</dt>
        <dd>
          {{ actividad.estado_gps || '—' }}
          <span v-if="actividad.latitud">({{ actividad.latitud }}, {{ actividad.longitud }})</span>
        </dd>
      </dl>

      <h2 class="eca-titulo">Evidencias</h2>
      <p v-if="!actividad.evidencias.length" class="eca-ayuda">Sin fotos.</p>
      <div v-else class="detalle__galeria">
        <figure v-for="e in actividad.evidencias" :key="e.uuid" class="detalle__foto">
          <img v-if="vistasPrevias[e.id]" :src="vistasPrevias[e.id]" :alt="e.nombre_archivo" />
          <figcaption>
            {{ e.nombre_archivo }}
            <button type="button" class="eca-btn eca-btn-secundario" @click="descargarEvidencia(e.id, e.nombre_archivo)">
              Descargar
            </button>
          </figcaption>
        </figure>
      </div>
    </template>
  </section>
</template>

<style scoped>
.detalle__datos {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.3rem 1rem;
  margin: 1rem 0;
}
.detalle__datos dd {
  margin: 0;
}
.detalle__galeria {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}
.detalle__foto {
  margin: 0;
  width: 180px;
}
.detalle__foto img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border-radius: var(--eca-r-sm);
  box-shadow: var(--eca-shadow-card);
}
.detalle__foto figcaption {
  font-size: 0.8rem;
  margin-top: 0.35rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
</style>
