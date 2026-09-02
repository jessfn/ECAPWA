<!-- pwa-eca — pantalla "Sincronización" (ECA-016 + ECA-017). Rediseño
     pedido explícito: mismo lenguaje visual e iconos profesionales que
     el resto de la app ya alineada con pwasuper. pwasuper en sí no tiene
     una pantalla dedicada de historial de sincronización (solo un
     indicador global de conectividad, `ConnectivityStatus.vue`, sin
     lista por ítem) — aquí se conserva la utilidad real que pwa-eca ya
     tenía (lista de pendientes con su estado y error) porque es más
     completa, pero con el mismo tipo de banner de estado por color
     (rojo sin conexión / azul sincronizando / ámbar pendientes / verde
     al día) e iconos de línea (AuthIcon) en vez de texto plano. -->
<script setup>
import { computed, ref, onMounted } from 'vue'
import { useOutboxStore } from '../stores/outbox'
import { useAuthStore } from '../stores/auth'
import { useConectividad } from '../services/conectividad'
import { sincronizar } from '../services/sync'
import BackButton from '../components/BackButton.vue'
import AuthIcon from '../components/auth/AuthIcon.vue'

const outbox = useOutboxStore()
const auth = useAuthStore()
const { enLinea } = useConectividad()
const sincronizando = ref(false)
const mensaje = ref('')

const ICONOS_TIPO = { jornada: 'login', actividad: 'briefcase', evidencia: 'camera' }
const ETIQUETAS_TIPO = { jornada: 'Jornada', actividad: 'Actividad', evidencia: 'Foto' }
const ETIQUETAS_ESTADO = {
  PENDIENTE: 'Pendiente de sincronizar',
  SINCRONIZANDO: 'Sincronizando…',
  SINCRONIZADO: 'Sincronizado',
  RECHAZADO: 'Rechazado por el servidor',
}

const MOTIVOS = {
  sin_red: 'Sin conexión. Se reintentará automáticamente al recuperarla.',
  sin_sesion: 'No se pudo recuperar tu sesión. Vuelve a iniciar sesión para sincronizar.',
  error_red: 'Hubo un error de red. Tus datos siguen guardados, se reintentará.',
  nada_pendiente: 'No había nada pendiente.',
  ya_en_curso: 'Ya hay una sincronización en curso.',
}

// Estado del banner superior — mismo criterio de semáforo que el
// indicador global de pwasuper (`ConnectivityStatus.vue`): rojo sin
// conexión, azul sincronizando, ámbar con pendientes, verde al día.
const estadoBanner = computed(() => {
  if (!enLinea.value) {
    return {
      clase: 'sincronizacion-banner--offline',
      icono: 'wifi-off',
      titulo: 'Sin conexión',
      subtitulo: 'Se reintentará automáticamente al recuperarla.',
    }
  }
  if (sincronizando.value) {
    return {
      clase: 'sincronizacion-banner--sincronizando',
      icono: 'sync',
      titulo: 'Sincronizando…',
      subtitulo: 'Enviando lo pendiente al servidor.',
    }
  }
  if (outbox.pendientes > 0) {
    return {
      clase: 'sincronizacion-banner--pendiente',
      icono: 'clock',
      titulo: `${outbox.pendientes} pendiente${outbox.pendientes === 1 ? '' : 's'} por enviar`,
      subtitulo: 'Se guardó en tu dispositivo; toca "Sincronizar ahora".',
    }
  }
  return {
    clase: 'sincronizacion-banner--al-dia',
    icono: 'check',
    titulo: 'Todo sincronizado',
    subtitulo: 'No hay nada pendiente por enviar.',
  }
})

async function sincronizarAhora() {
  sincronizando.value = true
  mensaje.value = ''
  try {
    const resultado = await sincronizar(auth)
    if (resultado.ok && resultado.motivo) {
      mensaje.value = MOTIVOS[resultado.motivo]
    } else if (resultado.ok) {
      mensaje.value = `Sincronizado: ${resultado.aplicados} nuevo(s), ${resultado.duplicados} ya estaban, ${resultado.rechazados} rechazado(s).`
    } else {
      mensaje.value = MOTIVOS[resultado.motivo] || 'No se pudo sincronizar.'
    }
  } finally {
    sincronizando.value = false
    await outbox.refrescar()
  }
}

onMounted(() => {
  outbox.refrescar()
})
</script>

<template>
  <main class="eca-contenido">
    <BackButton class="eca-entrar" />

    <div class="eca-card eca-entrar" style="--eca-delay: 0.06s">
      <h1 class="eca-titulo">Sincronización</h1>
      <p class="eca-ayuda">
        Todo lo que registras en la app se guarda primero en tu dispositivo. Esta pantalla muestra
        qué falta por enviar al servidor.
      </p>

      <div class="sincronizacion-banner" :class="estadoBanner.clase">
        <span class="sincronizacion-banner__icono" :class="{ 'sincronizacion-banner__icono--girando': sincronizando }">
          <AuthIcon :name="estadoBanner.icono" />
        </span>
        <span class="sincronizacion-banner__texto">
          <strong>{{ estadoBanner.titulo }}</strong>
          <span>{{ estadoBanner.subtitulo }}</span>
        </span>
      </div>

      <button
        type="button"
        class="eca-btn eca-btn-primary sincronizacion__boton"
        :disabled="sincronizando || !enLinea"
        @click="sincronizarAhora"
      >
        <AuthIcon name="sync" :class="{ 'sincronizacion__boton-icono--girando': sincronizando }" />
        {{ sincronizando ? 'Sincronizando…' : 'Sincronizar ahora' }}
      </button>

      <p v-if="mensaje" class="eca-alerta-ok sincronizacion__mensaje">{{ mensaje }}</p>

      <div v-if="!outbox.items.length" class="sincronizacion__vacio">
        <AuthIcon name="check" />
        <p>No hay nada pendiente</p>
      </div>

      <ul v-else class="eca-lista-limpia sincronizacion__lista">
        <li
          v-for="item in outbox.items"
          :key="item.uuid"
          class="sync-item"
          :class="`sync-item--${item.estado_local.toLowerCase()}`"
        >
          <span class="sync-item__icono">
            <AuthIcon :name="ICONOS_TIPO[item.tipo]" />
          </span>
          <span class="sync-item__cuerpo">
            <span class="sync-item__tipo">{{ ETIQUETAS_TIPO[item.tipo] }}</span>
            <span class="sync-item__estado">{{ ETIQUETAS_ESTADO[item.estado_local] }}</span>
            <span v-if="item.ultimo_error" class="sync-item__error">{{ item.ultimo_error }}</span>
          </span>
        </li>
      </ul>
    </div>
  </main>
</template>

<style scoped>
/* Banner de estado — mismo semáforo de colores que
   `ConnectivityStatus.vue` en pwasuper (rojo/azul/ámbar/verde). */
.sincronizacion-banner {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.75rem 0.9rem;
  border-radius: var(--eca-r-md);
  margin: 0.85rem 0;
}
.sincronizacion-banner__icono {
  flex-shrink: 0;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.35);
}
.sincronizacion-banner__icono svg {
  width: 1.15rem;
  height: 1.15rem;
}
.sincronizacion-banner__icono--girando svg {
  animation: sincronizacion-girar 1.1s linear infinite;
}
@keyframes sincronizacion-girar {
  to {
    transform: rotate(360deg);
  }
}
.sincronizacion-banner__texto {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  font-size: 0.85rem;
}
.sincronizacion-banner__texto strong {
  font-size: 0.92rem;
}

.sincronizacion-banner--offline {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #fff;
}
.sincronizacion-banner--sincronizando {
  background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
  color: #fff;
}
.sincronizacion-banner--pendiente {
  background: var(--eca-warn-bg);
  color: var(--eca-warn);
}
.sincronizacion-banner--al-dia {
  background: var(--eca-green-100);
  color: var(--eca-green-800);
}

.sincronizacion__boton {
  width: 100%;
}
.sincronizacion__boton svg {
  width: 1.05rem;
  height: 1.05rem;
}
.sincronizacion__boton-icono--girando {
  animation: sincronizacion-girar 1.1s linear infinite;
}

.sincronizacion__mensaje {
  margin-top: 0.75rem;
}

.sincronizacion__vacio {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 1.5rem 1rem;
  color: var(--eca-green-700);
}
.sincronizacion__vacio svg {
  width: 1.8rem;
  height: 1.8rem;
}
.sincronizacion__vacio p {
  margin: 0;
  font-weight: 700;
}

.sincronizacion__lista {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.sync-item {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.65rem 0.85rem;
  border-radius: var(--eca-r-sm);
  background: var(--eca-surface);
}
.sync-item__icono {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  color: var(--eca-ink-soft);
  box-shadow: var(--eca-shadow-card);
}
.sync-item__icono svg {
  width: 0.95rem;
  height: 0.95rem;
}
.sync-item__cuerpo {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.sync-item__tipo {
  font-weight: 700;
  color: var(--eca-green-800);
  font-size: 0.85rem;
}
.sync-item__estado {
  font-size: 0.82rem;
  color: var(--eca-ink-soft);
}
.sync-item--rechazado {
  background: var(--eca-danger-bg);
}
.sync-item--rechazado .sync-item__icono {
  color: var(--eca-danger);
}
.sync-item--sincronizado {
  background: var(--eca-green-100);
}
.sync-item--sincronizado .sync-item__icono {
  color: var(--eca-green-700);
}
.sync-item__error {
  color: var(--eca-danger);
  font-size: 0.8rem;
}
</style>
