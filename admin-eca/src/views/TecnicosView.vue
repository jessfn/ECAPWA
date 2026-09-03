<!-- admin-eca — pantalla "Técnicos" (nueva). Pedido explícito: mismo
     lenguaje visual que `UsuariosView.vue` de admin-pwa — header con
     ícono, tarjetas de estadística, buscador + chips de filtro por
     estado, tabla con avatar/badges, y una acción real (cambiar estado)
     en vez de una tabla de solo lectura. Consume `GET /usuarios`
     (permiso `usuarios.gestionar`) — el backend no pagina esta lista
     (a diferencia de `/actividades`), así que se filtra/pagina en el
     cliente, igual que hace admin-pwa con sus propias listas. -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../services/api'
import AuthIcon from '../components/auth/AuthIcon.vue'

const usuarios = ref([])
const cargando = ref(false)
const error = ref('')
const busqueda = ref('')
const filtroEstado = ref('TODOS')
const cambiandoEstado = ref(null) // id del usuario cuyo estado se está guardando

const ETIQUETAS_ROL = { ADMIN: 'Administrador', TECNICO: 'Técnico de campo' }
const ETIQUETAS_ESTADO = { ACTIVO: 'Activo', SUSPENDIDO: 'Suspendido', BAJA: 'Baja' }
const BADGE_ESTADO = { ACTIVO: 'eca-badge--verde', SUSPENDIDO: 'eca-badge--ambar', BAJA: 'eca-badge--rojo' }

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await api.get('/usuarios')
    usuarios.value = data
  } catch {
    error.value = 'No se pudieron cargar los técnicos.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

const stats = computed(() => ({
  total: usuarios.value.length,
  activos: usuarios.value.filter((u) => u.estado === 'ACTIVO').length,
  suspendidos: usuarios.value.filter((u) => u.estado === 'SUSPENDIDO').length,
  baja: usuarios.value.filter((u) => u.estado === 'BAJA').length,
}))

const usuariosFiltrados = computed(() => {
  const texto = busqueda.value.trim().toLowerCase()
  return usuarios.value.filter((u) => {
    if (filtroEstado.value !== 'TODOS' && u.estado !== filtroEstado.value) return false
    if (!texto) return true
    const nombreCompleto = `${u.nombre} ${u.apellido_paterno} ${u.apellido_materno || ''}`.toLowerCase()
    return nombreCompleto.includes(texto) || u.correo.toLowerCase().includes(texto)
  })
})

function iniciales(u) {
  const n = (u.nombre || '').trim()
  const a = (u.apellido_paterno || '').trim()
  if (n && a) return (n[0] + a[0]).toUpperCase()
  return n ? n.slice(0, 2).toUpperCase() : '??'
}
function nombreCompleto(u) {
  return [u.nombre, u.apellido_paterno, u.apellido_materno].filter(Boolean).join(' ')
}
function formatearFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
}

// Cambiar estado es una acción real y con efecto inmediato en el acceso
// del técnico a la app — se pide confirmación antes de aplicarla, igual
// que cualquier otra acción irreversible/sensible de este panel.
async function cambiarEstado(usuario, estadoNuevo) {
  if (estadoNuevo === usuario.estado) return
  const etiqueta = ETIQUETAS_ESTADO[estadoNuevo]
  const confirma = window.confirm(
    `¿Cambiar el estado de ${nombreCompleto(usuario)} a "${etiqueta}"? Esto afecta su acceso a la app de inmediato.`,
  )
  if (!confirma) return

  cambiandoEstado.value = usuario.id
  error.value = ''
  try {
    const { data } = await api.patch(`/usuarios/${usuario.id}/estado`, { estado: estadoNuevo })
    const indice = usuarios.value.findIndex((u) => u.id === usuario.id)
    if (indice !== -1) usuarios.value[indice] = data
  } catch {
    error.value = 'No se pudo cambiar el estado del técnico.'
  } finally {
    cambiandoEstado.value = null
  }
}
</script>

<template>
  <section>
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="user" /></span>
      <div class="eca-page-header__texto">
        <h1>Técnicos</h1>
        <p>Personal registrado en la app, con su rol y estado de cuenta.</p>
      </div>
      <button
        type="button"
        class="eca-page-header__accion"
        :class="{ 'eca-page-header__accion--girando': cargando }"
        :disabled="cargando"
        aria-label="Recargar"
        @click="cargar"
      >
        <AuthIcon name="sync" />
      </button>
    </div>

    <div class="eca-panel-fusionado">
      <p v-if="error" class="eca-alerta-error" role="alert">{{ error }}</p>

      <div class="eca-stats-grid">
        <div class="eca-stat-card eca-stat-card--morado">
          <span class="eca-stat-card__icono"><AuthIcon name="user" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.total }}</div><div class="eca-stat-card__etiqueta">Total</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--verde">
          <span class="eca-stat-card__icono"><AuthIcon name="check-circle" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.activos }}</div><div class="eca-stat-card__etiqueta">Activos</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--ambar">
          <span class="eca-stat-card__icono"><AuthIcon name="alert" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.suspendidos }}</div><div class="eca-stat-card__etiqueta">Suspendidos</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--rojo">
          <span class="eca-stat-card__icono"><AuthIcon name="close" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.baja }}</div><div class="eca-stat-card__etiqueta">Baja</div></div>
        </div>
      </div>

      <div class="tecnicos__controles">
        <label class="eca-search">
          <AuthIcon name="search" />
          <input v-model="busqueda" type="text" placeholder="Buscar por nombre o correo…" />
        </label>
        <div class="eca-chips">
          <button
            v-for="opcion in [
              { valor: 'TODOS', etiqueta: 'Todos' },
              { valor: 'ACTIVO', etiqueta: 'Activos' },
              { valor: 'SUSPENDIDO', etiqueta: 'Suspendidos' },
              { valor: 'BAJA', etiqueta: 'Baja' },
            ]"
            :key="opcion.valor"
            type="button"
            class="eca-chip"
            :class="{ 'eca-chip--activo': filtroEstado === opcion.valor }"
            @click="filtroEstado = opcion.valor"
          >
            {{ opcion.etiqueta }}
          </button>
        </div>
      </div>
    </div>

    <div class="eca-card">
      <p v-if="cargando" class="eca-ayuda">Cargando…</p>

      <div v-else-if="!usuariosFiltrados.length" class="eca-vacio">
        <AuthIcon name="user" />
        <p>{{ usuarios.length ? 'Ningún técnico coincide con la búsqueda.' : 'Todavía no hay técnicos registrados.' }}</p>
      </div>

      <div v-else class="eca-tabla-scroll">
        <table class="eca-tabla">
          <thead>
            <tr>
              <th>Técnico</th>
              <th>Teléfono</th>
              <th>Rol</th>
              <th>Estado</th>
              <th>Alta</th>
              <th>Último acceso</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in usuariosFiltrados" :key="u.id">
              <td>
                <div class="eca-tabla__usuario">
                  <span class="eca-avatar">{{ iniciales(u) }}</span>
                  <span class="eca-tabla__usuario-texto">
                    <strong>{{ nombreCompleto(u) }}</strong>
                    <span>{{ u.correo }}</span>
                  </span>
                </div>
              </td>
              <td>{{ u.telefono || '—' }}</td>
              <td>
                <span class="eca-badge eca-badge--morado">{{ ETIQUETAS_ROL[u.roles?.[0]] || u.roles?.[0] || '—' }}</span>
              </td>
              <td>
                <span class="eca-badge" :class="BADGE_ESTADO[u.estado]">{{ ETIQUETAS_ESTADO[u.estado] || u.estado }}</span>
              </td>
              <td>{{ formatearFecha(u.creado_en) }}</td>
              <td>{{ formatearFecha(u.ultimo_acceso_en) }}</td>
              <td>
                <select
                  class="tecnicos__select-estado"
                  :value="u.estado"
                  :disabled="cambiandoEstado === u.id"
                  @change="cambiarEstado(u, $event.target.value)"
                >
                  <option value="ACTIVO">Activar</option>
                  <option value="SUSPENDIDO">Suspender</option>
                  <option value="BAJA">Dar de baja</option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p class="eca-ayuda tecnicos__conteo">{{ usuariosFiltrados.length }} de {{ usuarios.length }} técnico(s).</p>
    </div>
  </section>
</template>

<style scoped>
.tecnicos__controles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1rem;
}
.eca-tabla-scroll {
  overflow-x: auto;
}
.tecnicos__select-estado {
  padding: 0.35rem 0.5rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
  font-size: 0.8rem;
  font-family: inherit;
  background: #fff;
}
.tecnicos__conteo {
  margin: 0.75rem 0 0;
}
</style>
