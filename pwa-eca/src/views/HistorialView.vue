<!-- pwa-eca — pantalla "Historial" (ECA-019).
     Combina lo local (outbox) con lo del servidor. El indicador
     "sin sincronizar" se calcula del `estado_local` del outbox — nunca de
     una columna de la BD (§2.3): una actividad ya en el servidor no
     necesita su registro de outbox para mostrarse como "Sincronizada". -->
<script setup>
import { ref, onMounted } from 'vue'
import { listar } from '../services/outbox'
import { listarMisActividades } from '../services/actividadesService'
import { useConectividad } from '../services/conectividad'
import ActividadCard from '../components/ActividadCard.vue'
import BackButton from '../components/BackButton.vue'

const { enLinea } = useConectividad()
const items = ref([])
const cargando = ref(false)
const error = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const locales = await listar('outbox_actividades')
    const porUuid = new Map()

    for (const local of locales) {
      porUuid.set(local.uuid, { actividad: local, estadoSincronizacion: local.estado_local })
    }

    if (enLinea.value) {
      try {
        const { resultados } = await listarMisActividades({ page_size: 100 })
        for (const remota of resultados) {
          porUuid.set(remota.uuid, { actividad: remota, estadoSincronizacion: 'SINCRONIZADO' })
        }
      } catch {
        error.value = 'No se pudo consultar el historial del servidor; se muestra lo guardado en el dispositivo.'
      }
    }

    items.value = [...porUuid.values()].sort(
      (a, b) => new Date(b.actividad.fecha_hora) - new Date(a.actividad.fecha_hora),
    )
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <div class="eca-card eca-entrar" style="--eca-delay: 0.06s">
      <h1 class="eca-titulo">Historial</h1>
      <p class="eca-ayuda">Tus actividades, guardadas en el dispositivo y en el servidor.</p>

      <p v-if="error" class="eca-alerta-aviso">{{ error }}</p>
      <p v-if="cargando" class="eca-ayuda">Cargando…</p>
      <p v-else-if="!items.length" class="eca-ayuda">Todavía no registras actividades.</p>

      <div v-else class="historial__lista">
        <ActividadCard
          v-for="item in items"
          :key="item.actividad.uuid"
          :actividad="item.actividad"
          :estado-sincronizacion="item.estadoSincronizacion"
        />
      </div>
    </div>
  </main>
</template>

<style scoped>
.historial__lista {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-top: 0.75rem;
}
</style>
