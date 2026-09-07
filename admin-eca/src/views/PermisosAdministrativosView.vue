<!-- admin-eca — pantalla "Permisos administrativos" (ECA-021): alta y
     gestión de las cuentas que entran al PANEL (nunca técnicos — esos
     viven en Técnicos). Solo dos roles posibles aquí:
       - ADMIN: acceso a todo, no se edita permiso por permiso.
       - USUARIO: sin ningún permiso propio en su rol (ver migración 0022)
         — todo lo que puede hacer sale de `usuarios_permisos`, otorgado
         uno por uno desde el modal de esta vista.
     Todo cambio (alta, rol, estado, permisos) actualiza el arreglo local
     en el momento — nunca se recarga la página ni se vuelve a pedir la
     lista completa, pedido explícito de que sea "reactivo". -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { api } from '../services/api'
import { listarPermisos, asignarPermisos } from '../services/permisosService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()

const usuarios = ref([])
const permisosCatalogo = ref([])
const cargando = ref(true)
const error = ref('')
const busqueda = ref('')
const filtroRol = ref('TODOS')

const ETIQUETA_ROL = { ADMIN: 'Administrador', USUARIO: 'Usuario' }
const ETIQUETA_ESTADO = { ACTIVO: 'Activo', SUSPENDIDO: 'Suspendido', BAJA: 'Baja' }
const BADGE_ESTADO = { ACTIVO: 'eca-badge--verde', SUSPENDIDO: 'eca-badge--ambar', BAJA: 'eca-badge--rojo' }

// Solo cuentas de PANEL (admin/usuario) — los técnicos se gestionan en
// su propia vista, aunque compartan la misma tabla `usuarios` de fondo.
const usuariosPanel = computed(() => usuarios.value.filter((u) => u.roles?.some((r) => r === 'ADMIN' || r === 'USUARIO')))
const filtrados = computed(() => {
  let lista = usuariosPanel.value
  if (filtroRol.value !== 'TODOS') lista = lista.filter((u) => u.roles.includes(filtroRol.value))
  const q = busqueda.value.trim().toLowerCase()
  if (!q) return lista
  return lista.filter((u) => `${u.nombre} ${u.apellido_paterno} ${u.correo}`.toLowerCase().includes(q))
})
const stats = computed(() => ({
  total: usuariosPanel.value.length,
  admins: usuariosPanel.value.filter((u) => u.roles.includes('ADMIN')).length,
  usuarios: usuariosPanel.value.filter((u) => u.roles.includes('USUARIO')).length,
  activos: usuariosPanel.value.filter((u) => u.estado === 'ACTIVO').length,
}))
const permisosPorModulo = computed(() => {
  const mapa = new Map()
  for (const p of permisosCatalogo.value) {
    if (!mapa.has(p.modulo)) mapa.set(p.modulo, [])
    mapa.get(p.modulo).push(p)
  }
  return mapa
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
function rolPrincipal(u) {
  return u.roles.includes('ADMIN') ? 'ADMIN' : 'USUARIO'
}
function esUnoMismo(u) {
  return auth.usuario?.id === u.id
}
function actualizarEnLista(usuarioActualizado) {
  const indice = usuarios.value.findIndex((u) => u.id === usuarioActualizado.id)
  if (indice !== -1) usuarios.value[indice] = usuarioActualizado
  else usuarios.value = [usuarioActualizado, ...usuarios.value]
}

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const [{ data: listaUsuarios }, listaPermisos] = await Promise.all([
      api.get('/usuarios'),
      listarPermisos(),
    ])
    usuarios.value = listaUsuarios
    permisosCatalogo.value = listaPermisos
  } catch {
    error.value = 'No se pudieron cargar los usuarios del panel.'
  } finally {
    cargando.value = false
  }
}
onMounted(cargar)

// ---- Crear usuario ----
const modalCrearAbierto = ref(false)
const nuevo = ref({ nombre: '', apellidoPaterno: '', apellidoMaterno: '', correo: '', telefono: '', rol: 'USUARIO' })
const creando = ref(false)
const errorCrear = ref('')
const resultadoCreado = ref(null)

function abrirModalCrear() {
  nuevo.value = { nombre: '', apellidoPaterno: '', apellidoMaterno: '', correo: '', telefono: '', rol: 'USUARIO' }
  errorCrear.value = ''
  resultadoCreado.value = null
  modalCrearAbierto.value = true
}
function cerrarModalCrear() {
  modalCrearAbierto.value = false
}
async function crearUsuario() {
  creando.value = true
  errorCrear.value = ''
  try {
    const { data } = await api.post('/usuarios', {
      nombre: nuevo.value.nombre.trim(),
      apellido_paterno: nuevo.value.apellidoPaterno.trim(),
      apellido_materno: nuevo.value.apellidoMaterno.trim() || null,
      correo: nuevo.value.correo.trim(),
      telefono: nuevo.value.telefono.trim() || null,
      roles: [nuevo.value.rol],
    })
    resultadoCreado.value = data
    actualizarEnLista(data.usuario)
  } catch (err) {
    errorCrear.value = err.response?.data?.error?.message || 'No se pudo crear el usuario.'
  } finally {
    creando.value = false
  }
}

// ---- Permisos (rol USUARIO) ----
const modalPermisosAbierto = ref(false)
const usuarioEditando = ref(null)
const permisosSeleccionados = ref(new Set())
const guardandoPermisos = ref(false)
const errorPermisos = ref('')

function abrirModalPermisos(usuario) {
  usuarioEditando.value = usuario
  permisosSeleccionados.value = new Set(usuario.permisos_directos || [])
  errorPermisos.value = ''
  modalPermisosAbierto.value = true
}
function cerrarModalPermisos() {
  modalPermisosAbierto.value = false
  usuarioEditando.value = null
}
function alternarPermiso(clave) {
  const nuevoSet = new Set(permisosSeleccionados.value)
  if (nuevoSet.has(clave)) nuevoSet.delete(clave)
  else nuevoSet.add(clave)
  permisosSeleccionados.value = nuevoSet
}
function alternarModuloCompleto(permisosDelModulo) {
  const claves = permisosDelModulo.map((p) => p.clave)
  const todosMarcados = claves.every((c) => permisosSeleccionados.value.has(c))
  const nuevoSet = new Set(permisosSeleccionados.value)
  for (const c of claves) {
    if (todosMarcados) nuevoSet.delete(c)
    else nuevoSet.add(c)
  }
  permisosSeleccionados.value = nuevoSet
}
async function guardarPermisos() {
  guardandoPermisos.value = true
  errorPermisos.value = ''
  try {
    const actualizado = await asignarPermisos(usuarioEditando.value.id, [...permisosSeleccionados.value])
    actualizarEnLista(actualizado)
    cerrarModalPermisos()
  } catch (err) {
    errorPermisos.value = err.response?.data?.error?.message || 'No se pudieron guardar los permisos.'
  } finally {
    guardandoPermisos.value = false
  }
}

// ---- Cambiar rol / estado ----
async function cambiarRol(usuario, rolNuevo) {
  if (usuario.roles.includes(rolNuevo)) return
  const etiqueta = ETIQUETA_ROL[rolNuevo]
  if (!window.confirm(`¿Cambiar el rol de ${nombreCompleto(usuario)} a "${etiqueta}"?`)) return
  try {
    const { data } = await api.put(`/usuarios/${usuario.id}/roles`, { roles: [rolNuevo] })
    actualizarEnLista(data)
  } catch {
    error.value = 'No se pudo cambiar el rol.'
  }
}
async function cambiarEstado(usuario, estadoNuevo) {
  if (estadoNuevo === usuario.estado) return
  const etiqueta = ETIQUETA_ESTADO[estadoNuevo]
  if (!window.confirm(`¿Cambiar el estado de ${nombreCompleto(usuario)} a "${etiqueta}"? Esto afecta su acceso de inmediato.`)) return
  try {
    const { data } = await api.patch(`/usuarios/${usuario.id}/estado`, { estado: estadoNuevo })
    actualizarEnLista(data)
  } catch {
    error.value = 'No se pudo cambiar el estado.'
  }
}
</script>

<template>
  <section>
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="shield-check" /></span>
      <div class="eca-page-header__texto">
        <h1>Permisos administrativos</h1>
        <p>Usuarios con acceso al panel de administración y sus permisos.</p>
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
          <span class="eca-stat-card__icono"><AuthIcon name="shield-check" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.total }}</div><div class="eca-stat-card__etiqueta">Total en el panel</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--ambar">
          <span class="eca-stat-card__icono"><AuthIcon name="shield" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.admins }}</div><div class="eca-stat-card__etiqueta">Administradores</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--azul">
          <span class="eca-stat-card__icono"><AuthIcon name="user" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.usuarios }}</div><div class="eca-stat-card__etiqueta">Usuarios personalizados</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--verde">
          <span class="eca-stat-card__icono"><AuthIcon name="check-circle" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.activos }}</div><div class="eca-stat-card__etiqueta">Activos</div></div>
        </div>
      </div>

      <div class="permisos__controles">
        <label class="eca-search">
          <AuthIcon name="search" />
          <input v-model="busqueda" type="text" placeholder="Buscar por nombre o correo…" />
        </label>
        <div class="eca-chips">
          <button
            v-for="opcion in [{ v: 'TODOS', t: 'Todos' }, { v: 'ADMIN', t: 'Administradores' }, { v: 'USUARIO', t: 'Usuarios' }]"
            :key="opcion.v"
            type="button"
            class="eca-chip"
            :class="{ 'eca-chip--activo': filtroRol === opcion.v }"
            @click="filtroRol = opcion.v"
          >
            {{ opcion.t }}
          </button>
        </div>
        <button type="button" class="eca-btn eca-btn-primary permisos__nuevo" @click="abrirModalCrear">
          <AuthIcon name="user-plus" /> Nuevo usuario
        </button>
      </div>
    </div>

    <div class="eca-card">
      <p v-if="cargando" class="eca-ayuda">Cargando…</p>

      <div v-else-if="!filtrados.length" class="eca-vacio">
        <AuthIcon name="shield-check" />
        <p>{{ usuariosPanel.length ? 'Nadie coincide con la búsqueda.' : 'Todavía no hay usuarios de panel además de ti.' }}</p>
      </div>

      <div v-else class="permisos__tabla-contenedor">
        <table class="eca-tabla permisos__tabla">
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Rol</th>
              <th>Permisos</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in filtrados" :key="u.id">
              <td>
                <div class="eca-tabla__usuario">
                  <span class="eca-avatar">{{ iniciales(u) }}</span>
                  <span class="eca-tabla__usuario-texto">
                    <strong>{{ nombreCompleto(u) }}{{ esUnoMismo(u) ? ' (tú)' : '' }}</strong>
                    <span>{{ u.correo }}</span>
                  </span>
                </div>
              </td>
              <td>
                <select
                  class="permisos__select-rol"
                  :class="rolPrincipal(u) === 'ADMIN' ? 'permisos__select-rol--admin' : 'permisos__select-rol--usuario'"
                  :value="rolPrincipal(u)"
                  :disabled="esUnoMismo(u)"
                  :title="esUnoMismo(u) ? 'No puedes cambiar tu propio rol' : ''"
                  @change="cambiarRol(u, $event.target.value)"
                >
                  <option value="ADMIN">Administrador</option>
                  <option value="USUARIO">Usuario</option>
                </select>
              </td>
              <td>
                <span v-if="rolPrincipal(u) === 'ADMIN'" class="eca-badge eca-badge--ambar">
                  <AuthIcon name="shield" /> Todos
                </span>
                <button v-else type="button" class="permisos__ver-permisos" @click="abrirModalPermisos(u)">
                  {{ u.permisos_directos?.length || 0 }} / {{ permisosCatalogo.length }}
                </button>
              </td>
              <td>
                <span class="eca-badge" :class="BADGE_ESTADO[u.estado]">{{ ETIQUETA_ESTADO[u.estado] || u.estado }}</span>
              </td>
              <td>
                <div class="permisos__acciones">
                  <button
                    v-if="rolPrincipal(u) === 'USUARIO'"
                    type="button"
                    class="permisos__accion permisos__accion--permisos"
                    title="Editar permisos"
                    @click="abrirModalPermisos(u)"
                  >
                    <AuthIcon name="shield-check" />
                  </button>
                  <select
                    class="permisos__select-estado"
                    :value="u.estado"
                    :disabled="esUnoMismo(u)"
                    :title="esUnoMismo(u) ? 'No puedes cambiar tu propio estado' : ''"
                    @change="cambiarEstado(u, $event.target.value)"
                  >
                    <option value="ACTIVO">Activar</option>
                    <option value="SUSPENDIDO">Suspender</option>
                    <option value="BAJA">Dar de baja</option>
                  </select>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ============ Modal: crear usuario ============ -->
    <Teleport to="body">
      <Transition name="permisos-fondo">
        <div v-if="modalCrearAbierto" class="permisos__modal-fondo" @click.self="cerrarModalCrear">
          <Transition name="permisos-modal" appear>
            <div class="permisos__modal permisos__modal--chico" role="dialog" aria-modal="true">
              <button type="button" class="permisos__modal-cerrar" aria-label="Cerrar" @click="cerrarModalCrear">
                <AuthIcon name="close" />
              </button>

              <template v-if="!resultadoCreado">
                <div class="permisos__modal-cabecera">
                  <span class="permisos__modal-icono"><AuthIcon name="user-plus" /></span>
                  <div class="permisos__modal-titulo">
                    <h2>Nuevo usuario de panel</h2>
                    <p>Entra a admin-eca con el rol que elijas.</p>
                  </div>
                </div>
                <form class="permisos__form" @submit.prevent="crearUsuario">
                  <p v-if="errorCrear" class="eca-alerta-error" role="alert">{{ errorCrear }}</p>
                  <div class="permisos__form-fila">
                    <label>
                      Nombre
                      <input v-model="nuevo.nombre" type="text" required />
                    </label>
                    <label>
                      Apellido paterno
                      <input v-model="nuevo.apellidoPaterno" type="text" required />
                    </label>
                  </div>
                  <div class="permisos__form-fila">
                    <label>
                      Apellido materno (opcional)
                      <input v-model="nuevo.apellidoMaterno" type="text" />
                    </label>
                    <label>
                      Teléfono (opcional)
                      <input v-model="nuevo.telefono" type="text" />
                    </label>
                  </div>
                  <label>
                    Correo
                    <input v-model="nuevo.correo" type="email" required />
                  </label>
                  <label>
                    Rol
                    <select v-model="nuevo.rol">
                      <option value="USUARIO">Usuario — permisos personalizados</option>
                      <option value="ADMIN">Administrador — acceso a todo</option>
                    </select>
                  </label>
                  <button type="submit" class="eca-btn eca-btn-primary permisos__form-enviar" :disabled="creando">
                    {{ creando ? 'Creando…' : 'Crear usuario' }}
                  </button>
                </form>
              </template>

              <template v-else>
                <div class="permisos__modal-cabecera permisos__modal-cabecera--exito">
                  <span class="permisos__modal-icono"><AuthIcon name="check" /></span>
                  <div class="permisos__modal-titulo">
                    <h2>Usuario creado</h2>
                    <p>{{ resultadoCreado.usuario.correo }}</p>
                  </div>
                </div>
                <div class="permisos__exito-cuerpo">
                  <p class="eca-ayuda">
                    Contraseña temporal (compártela por un canal seguro; se le pedirá cambiarla al entrar):
                  </p>
                  <p class="permisos__password">{{ resultadoCreado.contrasena_temporal }}</p>
                  <p v-if="resultadoCreado.usuario.roles.includes('USUARIO')" class="eca-ayuda">
                    Recuerda asignarle permisos desde la tabla — por ahora no puede ver nada del panel.
                  </p>
                  <button type="button" class="eca-btn eca-btn-primary permisos__form-enviar" @click="cerrarModalCrear">
                    Listo
                  </button>
                </div>
              </template>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

    <!-- ============ Modal: editar permisos ============ -->
    <Teleport to="body">
      <Transition name="permisos-fondo">
        <div v-if="modalPermisosAbierto" class="permisos__modal-fondo" @click.self="cerrarModalPermisos">
          <Transition name="permisos-modal" appear>
            <div class="permisos__modal" role="dialog" aria-modal="true">
              <button type="button" class="permisos__modal-cerrar" aria-label="Cerrar" @click="cerrarModalPermisos">
                <AuthIcon name="close" />
              </button>

              <div class="permisos__modal-cabecera">
                <span class="permisos__modal-icono"><AuthIcon name="shield-check" /></span>
                <div class="permisos__modal-titulo">
                  <h2>Permisos de {{ usuarioEditando ? nombreCompleto(usuarioEditando) : '' }}</h2>
                  <p>{{ permisosSeleccionados.size }} de {{ permisosCatalogo.length }} permisos otorgados</p>
                </div>
              </div>

              <div class="permisos__modal-cuerpo">
                <p v-if="errorPermisos" class="eca-alerta-error" role="alert">{{ errorPermisos }}</p>

                <div v-for="[modulo, lista] in permisosPorModulo" :key="modulo" class="permisos__modulo">
                  <div class="permisos__modulo-cabecera">
                    <h3>{{ modulo }}</h3>
                    <button type="button" class="permisos__modulo-todo" @click="alternarModuloCompleto(lista)">
                      {{ lista.every((p) => permisosSeleccionados.has(p.clave)) ? 'Quitar todos' : 'Marcar todos' }}
                    </button>
                  </div>
                  <label v-for="p in lista" :key="p.clave" class="permisos__item">
                    <input
                      type="checkbox"
                      :checked="permisosSeleccionados.has(p.clave)"
                      @change="alternarPermiso(p.clave)"
                    />
                    <span>
                      <strong>{{ p.nombre }}</strong>
                      <small v-if="p.descripcion">{{ p.descripcion }}</small>
                    </span>
                  </label>
                </div>
              </div>

              <div class="permisos__modal-pie">
                <button type="button" class="eca-btn eca-btn-secundario" @click="cerrarModalPermisos">Cancelar</button>
                <button type="button" class="eca-btn eca-btn-primary" :disabled="guardandoPermisos" @click="guardarPermisos">
                  {{ guardandoPermisos ? 'Guardando…' : 'Guardar cambios' }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.permisos__controles {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}
.permisos__nuevo {
  margin-left: auto;
  white-space: nowrap;
}
.permisos__nuevo svg {
  width: 1rem;
  height: 1rem;
}

.permisos__tabla-contenedor {
  max-height: 60vh;
  overflow: auto;
  border-radius: var(--eca-r-md);
  border: 1px solid var(--eca-surface-border);
}
.permisos__tabla-contenedor::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
.permisos__tabla-contenedor::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 10px;
}
.permisos__tabla thead th {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--eca-surface);
  box-shadow: 0 1px 0 var(--eca-surface-border);
}

.permisos__select-rol,
.permisos__select-estado {
  padding: 0.35rem 0.55rem;
  border-radius: var(--eca-r-sm);
  border: 1px solid var(--eca-surface-border);
  font-size: 0.8rem;
  font-family: inherit;
  background: #fff;
  font-weight: 700;
}
.permisos__select-rol--admin {
  color: #92400e;
  border-color: #fbbf24;
  background: #fffbeb;
}
.permisos__select-rol--usuario {
  color: #1d4ed8;
  border-color: #93c5fd;
  background: #eff6ff;
}
.permisos__select-rol:disabled,
.permisos__select-estado:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.permisos__ver-permisos {
  border: 1px solid var(--eca-surface-border);
  background: var(--eca-surface);
  color: var(--eca-purple-700);
  font-weight: 700;
  font-size: 0.8rem;
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.permisos__ver-permisos:hover {
  background: #ede9fe;
}

.permisos__acciones {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.permisos__accion {
  width: 2.1rem;
  height: 2.1rem;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
}
.permisos__accion svg {
  width: 0.95rem;
  height: 0.95rem;
}
.permisos__accion:hover {
  transform: scale(1.12);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.22);
}
.permisos__accion--permisos {
  background: linear-gradient(135deg, var(--eca-purple-600), var(--eca-purple-500));
}

/* ---- Modales: mismo lenguaje visual "Apple 2026" que el de detalle de
   Actividades — fondo con blur, entrada tipo resorte, hoja completa en
   móvil. ---- */
.permisos__modal-fondo {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(20, 24, 20, 0.45);
  backdrop-filter: blur(10px) saturate(1.4);
  -webkit-backdrop-filter: blur(10px) saturate(1.4);
}
.permisos-fondo-enter-active,
.permisos-fondo-leave-active {
  transition: opacity 0.25s ease;
}
.permisos-fondo-enter-from,
.permisos-fondo-leave-to {
  opacity: 0;
}
.permisos__modal {
  position: relative;
  width: 100%;
  max-width: 640px;
  max-height: 88vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 28px;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.35), 0 2px 8px rgba(0, 0, 0, 0.1);
}
.permisos__modal--chico {
  max-width: 480px;
}
.permisos__modal::-webkit-scrollbar {
  width: 8px;
}
.permisos__modal::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 10px;
}
.permisos-modal-enter-active {
  transition: opacity 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.permisos-modal-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.permisos-modal-enter-from {
  opacity: 0;
  transform: scale(0.92) translateY(18px);
}
.permisos-modal-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(10px);
}
.permisos__modal-cerrar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 1;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.85);
  color: var(--eca-ink);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.2s ease;
}
.permisos__modal-cerrar:hover {
  transform: rotate(90deg) scale(1.08);
  background: #fff;
}
.permisos__modal-cerrar svg {
  width: 0.95rem;
  height: 0.95rem;
}
.permisos__modal-cabecera {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1.5rem 3rem 1.5rem 1.75rem;
  border-radius: 28px 28px 0 0;
  background: linear-gradient(135deg, #4caf50 0%, #45a049 50%, #2e7d32 100%);
  color: #fff;
}
.permisos__modal-cabecera--exito {
  background: linear-gradient(135deg, #34d399 0%, var(--eca-green-600) 100%);
}
.permisos__modal-icono {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: var(--eca-r-sm);
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.permisos__modal-titulo {
  flex: 1;
  min-width: 0;
}
.permisos__modal-titulo h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
}
.permisos__modal-titulo p {
  margin: 0.15rem 0 0;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.85);
}

.permisos__form {
  padding: 1.5rem 1.75rem 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}
.permisos__form label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--eca-ink-soft);
  flex: 1;
}
.permisos__form input,
.permisos__form select {
  padding: 0.6rem 0.75rem;
  border-radius: var(--eca-r-sm);
  border: 1.5px solid var(--eca-surface-border);
  font: inherit;
  font-size: 0.9rem;
  color: var(--eca-ink);
}
.permisos__form-fila {
  display: flex;
  gap: 0.8rem;
}
.permisos__form-enviar {
  width: 100%;
  margin-top: 0.3rem;
}

.permisos__exito-cuerpo {
  padding: 1.5rem 1.75rem 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.permisos__password {
  font-family: 'Courier New', monospace;
  font-size: 1.1rem;
  font-weight: 700;
  background: var(--eca-surface);
  border: 1px solid var(--eca-surface-border);
  border-radius: var(--eca-r-sm);
  padding: 0.6rem 0.9rem;
  text-align: center;
  letter-spacing: 0.05em;
}

.permisos__modal-cuerpo {
  padding: 1.25rem 1.75rem;
}
.permisos__modulo {
  margin-bottom: 1.25rem;
}
.permisos__modulo:last-child {
  margin-bottom: 0;
}
.permisos__modulo-cabecera {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--eca-surface-border);
}
.permisos__modulo-cabecera h3 {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--eca-purple-700);
}
.permisos__modulo-todo {
  border: none;
  background: none;
  color: var(--eca-green-700);
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  padding: 0.15rem 0.4rem;
}
.permisos__modulo-todo:hover {
  text-decoration: underline;
}
.permisos__item {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.45rem 0.3rem;
  border-radius: var(--eca-r-sm);
  cursor: pointer;
  transition: background 0.15s ease;
}
.permisos__item:hover {
  background: var(--eca-surface);
}
.permisos__item input {
  margin-top: 0.2rem;
  flex-shrink: 0;
  width: 1.05rem;
  height: 1.05rem;
  accent-color: var(--eca-green-600);
}
.permisos__item span {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  font-size: 0.85rem;
}
.permisos__item small {
  color: var(--eca-ink-soft);
  font-size: 0.75rem;
}

.permisos__modal-pie {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  padding: 1rem 1.75rem 1.5rem;
  border-top: 1px solid var(--eca-surface-border);
}

@media (max-width: 640px) {
  .permisos__modal-fondo {
    padding: 0;
    align-items: flex-end;
  }
  .permisos__modal {
    max-width: 100%;
    max-height: 92vh;
    border-radius: 24px 24px 0 0;
  }
  .permisos-modal-enter-from,
  .permisos-modal-leave-to {
    transform: translateY(100%);
  }
  .permisos__modal-cabecera,
  .permisos__modal-cabecera--exito {
    border-radius: 24px 24px 0 0;
  }
  .permisos__form-fila {
    flex-direction: column;
  }
  .permisos__nuevo {
    margin-left: 0;
    width: 100%;
  }
}
</style>
