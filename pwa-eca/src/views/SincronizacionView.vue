<!-- pwa-eca — pantalla "Sincronización" (ECA-016 + ECA-017).
     Muestra lo que hay en el outbox local y su `estado_local`, y permite
     forzar una sincronización manual. El motor solo actúa con red y
     sesión de servidor válida — sin eso, deja el outbox intacto y avisa. -->
<script setup>
import { ref, onMounted } from 'vue'
import { useOutboxStore } from '../stores/outbox'
import { useAuthStore } from '../stores/auth'
import { sincronizar } from '../services/sync'
import BackButton from '../components/BackButton.vue'

const outbox = useOutboxStore()
const auth = useAuthStore()
const sincronizando = ref(false)
const mensaje = ref('')

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

      <button type="button" class="eca-btn eca-btn-primary" :disabled="sincronizando" @click="sincronizarAhora">
        {{ sincronizando ? 'Sincronizando…' : 'Sincronizar ahora' }}
      </button>

      <p v-if="mensaje" class="eca-alerta-ok sincronizacion__mensaje">{{ mensaje }}</p>

      <p v-if="!outbox.items.length" class="eca-alerta-ok sincronizacion__mensaje">No hay nada pendiente.</p>

      <ul v-else class="eca-lista-limpia sincronizacion__lista">
        <li
          v-for="item in outbox.items"
          :key="item.uuid"
          class="sync-item"
          :class="`sync-item--${item.estado_local.toLowerCase()}`"
        >
          <span class="sync-item__tipo">{{ ETIQUETAS_TIPO[item.tipo] }}</span>
          <span>{{ ETIQUETAS_ESTADO[item.estado_local] }}</span>
          <span v-if="item.ultimo_error" class="sync-item__error">{{ item.ultimo_error }}</span>
        </li>
      </ul>
    </div>
  </main>
</template>

<style scoped>
.sincronizacion__mensaje {
  margin-top: 0.75rem;
}
.sincronizacion__lista {
  margin-top: 0.75rem;
}
.sync-item {
  display: flex;
  flex-direction: column;
  padding: 0.6rem 0.9rem;
  border-radius: var(--eca-r-sm);
  background: var(--eca-surface);
}
.sync-item--rechazado {
  background: var(--eca-danger-bg);
}
.sync-item--sincronizado {
  background: var(--eca-green-100);
}
.sync-item__tipo {
  font-weight: 700;
  color: var(--eca-green-800);
}
.sync-item__error {
  color: var(--eca-danger);
  font-size: 0.85rem;
}
</style>
