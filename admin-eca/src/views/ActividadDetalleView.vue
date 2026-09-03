<!-- admin-eca — pantalla "Detalle de actividad" (ECA-019): datos completos +
     galería de evidencias con descarga autenticada (nunca estático
     público). Rediseño pedido explícito: mismo lenguaje visual que el
     resto del panel (header, badges, avatar) en vez de una lista `<dl>`
     plana. Nombre del técnico y de la ECA son "mejor esfuerzo": si el
     admin actual no tiene permiso de `usuarios.gestionar` (distinto de
     `actividades.ver_todas`) o la ECA no se encuentra, se degrada a
     "Técnico #id"/"ECA #id" en vez de romper la pantalla. -->
<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { obtenerActividad, descargarEvidencia, urlVistaPreviaEvidencia } from '../services/actividadesService'
import { api } from '../services/api'
import { obtenerEca } from '../services/ecasService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const route = useRoute()
const actividad = ref(null)
const tecnico = ref(null)
const eca = ref(null)
const cargando = ref(true)
const error = ref('')
const vistasPrevias = ref({}) // evidenciaId -> object URL

const ETIQUETAS_GPS = { CON_GPS: 'Con GPS', GPS_IMPRECISO: 'GPS impreciso', SIN_GPS: 'Sin GPS' }
const BADGE_GPS = { CON_GPS: 'eca-badge--verde', GPS_IMPRECISO: 'eca-badge--ambar', SIN_GPS: 'eca-badge--gris' }

function iniciales(u) {
  const n = (u?.nombre || '').trim()
  const a = (u?.apellido_paterno || '').trim()
  if (n && a) return (n[0] + a[0]).toUpperCase()
  return '??'
}

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
    api
      .get(`/usuarios/${actividad.value.usuario_id}`)
      .then(({ data }) => (tecnico.value = data))
      .catch(() => {})
    if (actividad.value.eca_id) {
      obtenerEca(actividad.value.eca_id)
        .then((data) => (eca.value = data))
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
  <section>
    <RouterLink :to="{ name: 'actividades' }" class="detalle__volver">
      <AuthIcon name="arrow-left" /> Volver a Actividades
    </RouterLink>

    <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>
    <p v-if="cargando" class="eca-ayuda">Cargando…</p>

    <template v-else-if="actividad">
      <div class="eca-page-header">
        <span class="eca-page-header__icono"><AuthIcon name="clipboard" /></span>
        <div class="eca-page-header__texto">
          <h1>Detalle de actividad</h1>
          <p>{{ actividad.uuid }}</p>
        </div>
        <span class="eca-badge" :class="BADGE_GPS[actividad.estado_gps] || 'eca-badge--gris'">
          <AuthIcon name="map-pin" /> {{ ETIQUETAS_GPS[actividad.estado_gps] || '—' }}
        </span>
      </div>

      <div class="eca-card eca-panel-fusionado detalle__card">
        <div class="detalle__usuario">
          <span class="eca-avatar detalle__avatar">{{ iniciales(tecnico) }}</span>
          <div>
            <strong>{{ tecnico ? `${tecnico.nombre} ${tecnico.apellido_paterno}` : `Técnico #${actividad.usuario_id}` }}</strong>
            <span v-if="tecnico" class="eca-ayuda">{{ tecnico.correo }}</span>
          </div>
        </div>

        <dl class="detalle__datos">
          <dt>Fecha</dt>
          <dd>{{ new Date(actividad.fecha_hora).toLocaleString('es-MX') }}</dd>
          <dt>ECA</dt>
          <dd>{{ eca ? eca.nombre : (actividad.eca_id ? `ECA #${actividad.eca_id}` : '—') }}</dd>
          <dt>Descripción</dt>
          <dd>{{ actividad.descripcion }}</dd>
          <dt>Resultado</dt>
          <dd>{{ actividad.resultado || '—' }}</dd>
          <dt>Ubicación GPS</dt>
          <dd>
            <span v-if="actividad.latitud">{{ actividad.latitud }}, {{ actividad.longitud }} (±{{ Math.round(actividad.precision_gps_m || 0) }} m)</span>
            <span v-else>Sin coordenadas</span>
          </dd>
        </dl>
      </div>

      <div class="eca-card detalle__card">
        <h2 class="eca-page-subtitulo"><AuthIcon name="camera" /> Evidencias fotográficas</h2>
        <div v-if="!actividad.evidencias.length" class="eca-vacio">
          <AuthIcon name="camera" />
          <p>Sin fotos.</p>
        </div>
        <div v-else class="detalle__galeria">
          <figure v-for="e in actividad.evidencias" :key="e.uuid" class="detalle__foto">
            <img v-if="vistasPrevias[e.id]" :src="vistasPrevias[e.id]" :alt="e.nombre_archivo" />
            <div v-else class="detalle__foto-cargando">Cargando…</div>
            <figcaption>
              {{ e.nombre_archivo }}
              <button type="button" class="eca-btn eca-btn-secundario" @click="descargarEvidencia(e.id, e.nombre_archivo)">
                Descargar
              </button>
            </figcaption>
          </figure>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.detalle__volver {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--eca-purple-700);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}
.detalle__volver svg {
  width: 14px;
  height: 14px;
}
.detalle__card + .detalle__card {
  margin-top: 1rem;
}
.detalle__usuario {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--eca-surface-border);
}
.detalle__avatar {
  width: 2.6rem;
  height: 2.6rem;
  font-size: 0.85rem;
}
.detalle__usuario div {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.detalle__datos {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem 1.2rem;
  margin: 0;
}
.detalle__datos dt {
  color: var(--eca-ink-soft);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.detalle__datos dd {
  margin: 0;
}
.eca-page-subtitulo {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0 0 1rem;
  color: var(--eca-purple-700);
  font-size: 1rem;
}
.eca-page-subtitulo svg {
  width: 16px;
  height: 16px;
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
.detalle__foto img,
.detalle__foto-cargando {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border-radius: var(--eca-r-sm);
  box-shadow: var(--eca-shadow-card);
}
.detalle__foto-cargando {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--eca-surface);
  color: var(--eca-ink-soft);
  font-size: 0.8rem;
}
.detalle__foto figcaption {
  font-size: 0.8rem;
  margin-top: 0.35rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  word-break: break-all;
}
</style>
