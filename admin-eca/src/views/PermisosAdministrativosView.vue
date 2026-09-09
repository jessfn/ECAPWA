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

// Mismo orden (alfabético) y mismas vistas que `Sidebar.vue` — el switch de
// cada una prende/apaga exactamente el permiso `vista.*` que la muestra en el
// menú. `modulos` conecta cada vista con los permisos "finos" de sus secciones
// del catálogo (p. ej. `ecas.gestionar`), que solo tienen sentido si la vista
// ya está encendida. "Modificaciones" abarca VARIOS módulos (unifica ECA,
// Ámbitos, Asignaciones y Catálogos), por eso `modulos` es una lista.
const VISTAS = [
  { clave: 'vista.actividades', etiqueta: 'Actividades', icono: 'clock', modulos: ['actividades'] },
  { clave: 'vista.asistencia', etiqueta: 'Asistencia', icono: 'check-circle', modulos: ['jornadas'] },
  { clave: 'vista.modificaciones', etiqueta: 'Modificaciones', icono: 'edit', modulos: ['ecas', 'ambitos', 'asignaciones', 'catalogos'] },
  { clave: 'vista.permisos_administrativos', etiqueta: 'Permisos administrativos', icono: 'shield-check', modulos: [] },
  { clave: 'vista.tecnicos', etiqueta: 'Técnicos', icono: 'user', modulos: ['usuarios'] },
  { clave: 'vista.visor_seguimiento', etiqueta: 'Visor de Seguimiento', icono: 'map-pin', modulos: [] },
]

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
    if (p.clave.startsWith('vista.')) continue
    if (!mapa.has(p.modulo)) mapa.set(p.modulo, [])
    mapa.get(p.modulo).push(p)
  }
  return mapa
})
// Vistas + sus permisos finos, ya armado en el orden del sidebar — lo que
// consume directamente el modal de permisos. Una vista puede abarcar varios
// módulos (p. ej. "Modificaciones"), así que se juntan los sub-permisos de
// todos ellos.
const vistasConPermisos = computed(() =>
  VISTAS.map((v) => ({
    ...v,
    subPermisos: (v.modulos || []).flatMap((m) => permisosPorModulo.value.get(m) || []),
  })),
)

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
const nuevo = ref({ nombre: '', apellidoPaterno: '', apellidoMaterno: '', correo: '', telefono: '', rol: 'USUARIO', contrasena: '', confirmarContrasena: '' })
const nuevoPermisosSeleccionados = ref(new Set())
const mostrarContrasena = ref(false)
const mostrarConfirmar = ref(false)
const creando = ref(false)
const errorCrear = ref('')
const resultadoCreado = ref(null)

// Fuerza de contraseña: 0-4
const fuerzaContrasena = computed(() => {
  const p = nuevo.value.contrasena
  if (!p) return 0
  let score = 0
  if (p.length >= 10) score++
  if (p.length >= 14) score++
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score++
  if (/\d/.test(p)) score++
  if (/[^a-zA-Z0-9]/.test(p)) score++
  return Math.min(score, 4)
})
const fuerzaEtiqueta = computed(() => ['', 'Débil', 'Regular', 'Buena', 'Excelente'][fuerzaContrasena.value])
const fuerzaColor = computed(() => ['', '#ef4444', '#f97316', '#3b82f6', '#22c55e'][fuerzaContrasena.value])
const contrasenasCoinciden = computed(() =>
  nuevo.value.confirmarContrasena.length > 0 && nuevo.value.contrasena === nuevo.value.confirmarContrasena
)
const contrasenasNoCoinciden = computed(() =>
  nuevo.value.confirmarContrasena.length > 0 && nuevo.value.contrasena !== nuevo.value.confirmarContrasena
)
const formularioValido = computed(() =>
  nuevo.value.nombre.trim() &&
  nuevo.value.apellidoPaterno.trim() &&
  nuevo.value.correo.trim() &&
  nuevo.value.contrasena.length >= 10 &&
  /[a-zA-Z]/.test(nuevo.value.contrasena) &&
  /\d/.test(nuevo.value.contrasena) &&
  contrasenasCoinciden.value
)

function abrirModalCrear() {
  nuevo.value = { nombre: '', apellidoPaterno: '', apellidoMaterno: '', correo: '', telefono: '', rol: 'USUARIO', contrasena: '', confirmarContrasena: '' }
  nuevoPermisosSeleccionados.value = new Set()
  mostrarContrasena.value = false
  mostrarConfirmar.value = false
  errorCrear.value = ''
  resultadoCreado.value = null
  modalCrearAbierto.value = true
}
function cerrarModalCrear() {
  modalCrearAbierto.value = false
}
function nuevoVistaEncendida(vista) {
  return nuevoPermisosSeleccionados.value.has(vista.clave)
}
function alternarNuevaVista(vista) {
  const s = new Set(nuevoPermisosSeleccionados.value)
  if (s.has(vista.clave)) {
    s.delete(vista.clave)
    for (const p of vista.subPermisos) s.delete(p.clave)
  } else {
    s.add(vista.clave)
  }
  nuevoPermisosSeleccionados.value = s
}
function alternarNuevoPermiso(clave) {
  const s = new Set(nuevoPermisosSeleccionados.value)
  if (s.has(clave)) s.delete(clave)
  else s.add(clave)
  nuevoPermisosSeleccionados.value = s
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
      contrasena: nuevo.value.contrasena,
    })
    resultadoCreado.value = data
    actualizarEnLista(data.usuario)
    // Si es USUARIO y hay permisos seleccionados, asignarlos de inmediato
    if (nuevo.value.rol === 'USUARIO' && nuevoPermisosSeleccionados.value.size > 0) {
      const usuarioActualizado = await asignarPermisos(data.usuario.id, [...nuevoPermisosSeleccionados.value])
      if (usuarioActualizado) actualizarEnLista(usuarioActualizado)
    }
  } catch (err) {
    errorCrear.value = err.response?.data?.error?.message || 'No se pudo crear el usuario.'
  } finally {
    creando.value = false
  }
}

// ---- Editar usuario: datos + permisos en un mismo modal (rol USUARIO) ----
// Pedido explícito: el botón "Editar" de la tabla debe poder cambiar tanto
// los datos básicos como los permisos por vista, en un solo guardado.
const modalEditarAbierto = ref(false)
const usuarioEditando = ref(null)
const datosEditando = ref({ nombre: '', apellidoPaterno: '', apellidoMaterno: '', telefono: '', cargo: '' })
const permisosSeleccionados = ref(new Set())
const guardandoPermisos = ref(false)
const errorPermisos = ref('')

function abrirModalPermisos(usuario) {
  usuarioEditando.value = usuario
  datosEditando.value = {
    nombre: usuario.nombre || '',
    apellidoPaterno: usuario.apellido_paterno || '',
    apellidoMaterno: usuario.apellido_materno || '',
    telefono: usuario.telefono || '',
    cargo: usuario.cargo || '',
  }
  permisosSeleccionados.value = new Set(usuario.permisos_directos || [])
  errorPermisos.value = ''
  modalEditarAbierto.value = true
}
function cerrarModalPermisos() {
  modalEditarAbierto.value = false
  usuarioEditando.value = null
}
function vistaEncendida(vista) {
  return permisosSeleccionados.value.has(vista.clave)
}
// Apagar una vista no tiene sentido dejando prendidos sus permisos finos
// (ver Ámbitos sin poder ver la vista sería un permiso fantasma) — se
// apagan juntos. Prender la vista no prende sus sub-permisos: eso lo
// decide el admin aparte (p. ej. ver Ámbitos sin poder gestionarlos).
function alternarVista(vista) {
  const nuevoSet = new Set(permisosSeleccionados.value)
  if (nuevoSet.has(vista.clave)) {
    nuevoSet.delete(vista.clave)
    for (const p of vista.subPermisos) nuevoSet.delete(p.clave)
  } else {
    nuevoSet.add(vista.clave)
  }
  permisosSeleccionados.value = nuevoSet
}
function alternarPermiso(clave) {
  const nuevoSet = new Set(permisosSeleccionados.value)
  if (nuevoSet.has(clave)) nuevoSet.delete(clave)
  else nuevoSet.add(clave)
  permisosSeleccionados.value = nuevoSet
}
async function guardarPermisos() {
  guardandoPermisos.value = true
  errorPermisos.value = ''
  try {
    const { data: usuarioActualizado } = await api.patch(`/usuarios/${usuarioEditando.value.id}`, {
      nombre: datosEditando.value.nombre.trim(),
      apellido_paterno: datosEditando.value.apellidoPaterno.trim(),
      apellido_materno: datosEditando.value.apellidoMaterno.trim() || null,
      telefono: datosEditando.value.telefono.trim() || null,
      cargo: datosEditando.value.cargo.trim() || null,
    })
    // El rol ADMIN no tiene permisos directos que tocar (accede a todo por
    // rol) — solo se manda el `PUT /permisos` para el rol USUARIO, y su
    // respuesta (más fresca, con `permisos_directos` recalculados) es la
    // que queda en la lista.
    const permisosActualizado =
      rolPrincipal(usuarioEditando.value) === 'USUARIO'
        ? await asignarPermisos(usuarioEditando.value.id, [...permisosSeleccionados.value])
        : null
    actualizarEnLista(permisosActualizado || usuarioActualizado)
    cerrarModalPermisos()
  } catch (err) {
    errorPermisos.value = err.response?.data?.error?.message || 'No se pudieron guardar los cambios.'
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
                    type="button"
                    class="permisos__accion permisos__accion--editar"
                    title="Editar usuario"
                    @click="abrirModalPermisos(u)"
                  >
                    <AuthIcon name="edit" />
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
            <div class="permisos__modal" :class="nuevo.rol === 'USUARIO' ? '' : 'permisos__modal--chico'" role="dialog" aria-modal="true">
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

                <div class="permisos__modal-cuerpo">
                  <p v-if="errorCrear" class="eca-alerta-error" role="alert">{{ errorCrear }}</p>

                  <!-- Datos básicos -->
                  <div class="permisos__seccion">
                    <h3 class="permisos__seccion-titulo"><AuthIcon name="user" /> Datos</h3>
                    <div class="permisos__campos-fila">
                      <label class="permisos__campo">
                        <span>Nombre *</span>
                        <input v-model="nuevo.nombre" type="text" required />
                      </label>
                      <label class="permisos__campo">
                        <span>Apellido paterno *</span>
                        <input v-model="nuevo.apellidoPaterno" type="text" required />
                      </label>
                    </div>
                    <div class="permisos__campos-fila">
                      <label class="permisos__campo">
                        <span>Apellido materno</span>
                        <input v-model="nuevo.apellidoMaterno" type="text" placeholder="Opcional" />
                      </label>
                      <label class="permisos__campo">
                        <span>Teléfono</span>
                        <input v-model="nuevo.telefono" type="text" placeholder="Opcional" />
                      </label>
                    </div>
                    <label class="permisos__campo">
                      <span>Correo *</span>
                      <input v-model="nuevo.correo" type="email" required />
                    </label>
                    <label class="permisos__campo">
                      <span>Rol</span>
                      <select v-model="nuevo.rol" class="permisos__select-crear-rol">
                        <option value="USUARIO">Usuario — permisos personalizados</option>
                        <option value="ADMIN">Administrador — acceso a todo</option>
                      </select>
                    </label>
                  </div>

                  <!-- Contraseña -->
                  <div class="permisos__seccion">
                    <h3 class="permisos__seccion-titulo"><AuthIcon name="shield" /> Contraseña</h3>
                    <label class="permisos__campo">
                      <span>Contraseña *</span>
                      <div class="permisos__campo-ojo">
                        <input
                          v-model="nuevo.contrasena"
                          :type="mostrarContrasena ? 'text' : 'password'"
                          placeholder="Mínimo 10 caracteres, letras y números"
                          autocomplete="new-password"
                        />
                        <button type="button" class="permisos__ojo" @click="mostrarContrasena = !mostrarContrasena">
                          <AuthIcon :name="mostrarContrasena ? 'eye-off' : 'eye'" />
                        </button>
                      </div>
                      <!-- Barra de fuerza -->
                      <div v-if="nuevo.contrasena" class="permisos__fuerza">
                        <div class="permisos__fuerza-barras">
                          <span
                            v-for="i in 4"
                            :key="i"
                            class="permisos__fuerza-barra"
                            :style="{ background: i <= fuerzaContrasena ? fuerzaColor : undefined }"
                          />
                        </div>
                        <Transition name="permisos-copiar-icono" mode="out-in">
                          <span :key="fuerzaEtiqueta" class="permisos__fuerza-etiqueta" :style="{ color: fuerzaColor }">{{ fuerzaEtiqueta }}</span>
                        </Transition>
                      </div>
                    </label>
                    <label class="permisos__campo">
                      <span>Confirmar contraseña *</span>
                      <div class="permisos__campo-ojo permisos__campo-ojo--con-match">
                        <input
                          v-model="nuevo.confirmarContrasena"
                          :type="mostrarConfirmar ? 'text' : 'password'"
                          :class="{ 'permisos__input--ok': contrasenasCoinciden, 'permisos__input--error': contrasenasNoCoinciden }"
                          placeholder="Repite la contraseña"
                          autocomplete="new-password"
                        />
                        <button type="button" class="permisos__ojo" @click="mostrarConfirmar = !mostrarConfirmar">
                          <AuthIcon :name="mostrarConfirmar ? 'eye-off' : 'eye'" />
                        </button>
                        <Transition name="permisos-copiar-icono" mode="out-in">
                          <span v-if="contrasenasCoinciden" key="ok" class="permisos__match-icono permisos__match-icono--ok">
                            <AuthIcon name="check" />
                          </span>
                          <span v-else-if="contrasenasNoCoinciden" key="no" class="permisos__match-icono permisos__match-icono--no">
                            <AuthIcon name="close" />
                          </span>
                        </Transition>
                      </div>
                      <Transition name="permisos-subpermisos">
                        <p v-if="contrasenasNoCoinciden" class="permisos__campo-hint permisos__campo-hint--error">Las contraseñas no coinciden</p>
                      </Transition>
                    </label>
                  </div>

                  <!-- Permisos (solo USUARIO) -->
                  <div v-if="nuevo.rol === 'USUARIO'" class="permisos__seccion">
                    <h3 class="permisos__seccion-titulo"><AuthIcon name="shield-check" /> Acceso al panel</h3>
                    <p class="eca-ayuda permisos__ayuda-vistas">Activa las vistas a las que podrá entrar este usuario.</p>
                    <div v-for="vista in vistasConPermisos" :key="vista.clave" class="permisos__vista" :class="{ 'permisos__vista--activa': nuevoVistaEncendida(vista) }">
                      <div class="permisos__vista-fila">
                        <span class="permisos__vista-icono"><AuthIcon :name="vista.icono" /></span>
                        <span class="permisos__vista-etiqueta">{{ vista.etiqueta }}</span>
                        <label class="permisos__switch">
                          <input type="checkbox" :checked="nuevoVistaEncendida(vista)" @change="alternarNuevaVista(vista)" />
                          <span class="permisos__switch-riel"></span>
                        </label>
                      </div>
                      <Transition name="permisos-subpermisos">
                        <div v-if="vista.subPermisos.length && nuevoVistaEncendida(vista)" class="permisos__subpermisos">
                          <label v-for="p in vista.subPermisos" :key="p.clave" class="permisos__item">
                            <input type="checkbox" :checked="nuevoPermisosSeleccionados.has(p.clave)" @change="alternarNuevoPermiso(p.clave)" />
                            <span>{{ p.nombre }}</span>
                          </label>
                        </div>
                      </Transition>
                    </div>
                  </div>

                  <!-- ADMIN card -->
                  <div v-else class="permisos__seccion">
                    <div class="permisos__admin-total">
                      <span class="permisos__admin-total-icono"><AuthIcon name="shield" /></span>
                      <div>
                        <strong>Acceso completo</strong>
                        <p>Este administrador verá y gestionará todas las vistas del panel.</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="permisos__modal-pie">
                  <button type="button" class="eca-btn eca-btn-secundario" @click="cerrarModalCrear">Cancelar</button>
                  <button
                    type="button"
                    class="eca-btn eca-btn-primary"
                    :disabled="creando || !formularioValido"
                    :title="!formularioValido ? 'Completa todos los campos y verifica la contraseña' : ''"
                    @click="crearUsuario"
                  >
                    {{ creando ? 'Creando…' : 'Crear usuario' }}
                  </button>
                </div>
              </template>

              <template v-else>
                <div class="permisos__modal-cabecera permisos__modal-cabecera--exito">
                  <span class="permisos__modal-icono permisos__icono-exito"><AuthIcon name="check" /></span>
                  <div class="permisos__modal-titulo">
                    <h2>¡Usuario creado!</h2>
                    <p>{{ resultadoCreado.usuario.correo }}</p>
                  </div>
                </div>
                <div class="permisos__exito-cuerpo">
                  <div class="permisos__exito-info">
                    <div class="permisos__exito-fila">
                      <span class="permisos__exito-icono"><AuthIcon name="user" /></span>
                      <div>
                        <strong>{{ [resultadoCreado.usuario.nombre, resultadoCreado.usuario.apellido_paterno].join(' ') }}</strong>
                        <span>{{ ETIQUETA_ROL[resultadoCreado.usuario.roles[0]] || resultadoCreado.usuario.roles[0] }}</span>
                      </div>
                    </div>
                  </div>
                  <p class="eca-ayuda" style="text-align:center">Ya puede iniciar sesión con la contraseña que estableciste.</p>
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

    <!-- ============ Modal: editar usuario (datos + permisos) ============ -->
    <Teleport to="body">
      <Transition name="permisos-fondo">
        <div v-if="modalEditarAbierto" class="permisos__modal-fondo" @click.self="cerrarModalPermisos">
          <Transition name="permisos-modal" appear>
            <div class="permisos__modal" role="dialog" aria-modal="true">
              <button type="button" class="permisos__modal-cerrar" aria-label="Cerrar" @click="cerrarModalPermisos">
                <AuthIcon name="close" />
              </button>

              <div class="permisos__modal-cabecera">
                <span class="permisos__modal-icono"><AuthIcon name="edit" /></span>
                <div class="permisos__modal-titulo">
                  <h2>Editar {{ usuarioEditando ? nombreCompleto(usuarioEditando) : '' }}</h2>
                  <p v-if="usuarioEditando && rolPrincipal(usuarioEditando) === 'USUARIO'">
                    {{ permisosSeleccionados.size }} permiso(s) otorgados
                  </p>
                  <p v-else>Administrador — acceso a todo el panel</p>
                </div>
              </div>

              <div class="permisos__modal-cuerpo">
                <p v-if="errorPermisos" class="eca-alerta-error" role="alert">{{ errorPermisos }}</p>

                <div class="permisos__seccion">
                  <h3 class="permisos__seccion-titulo"><AuthIcon name="user" /> Datos</h3>
                  <div class="permisos__campos-fila">
                    <label class="permisos__campo">
                      <span>Nombre</span>
                      <input v-model="datosEditando.nombre" type="text" required />
                    </label>
                    <label class="permisos__campo">
                      <span>Apellido paterno</span>
                      <input v-model="datosEditando.apellidoPaterno" type="text" required />
                    </label>
                  </div>
                  <div class="permisos__campos-fila">
                    <label class="permisos__campo">
                      <span>Apellido materno</span>
                      <input v-model="datosEditando.apellidoMaterno" type="text" placeholder="Opcional" />
                    </label>
                    <label class="permisos__campo">
                      <span>Teléfono</span>
                      <input v-model="datosEditando.telefono" type="text" placeholder="Opcional" />
                    </label>
                  </div>
                  <label class="permisos__campo">
                    <span>Cargo</span>
                    <input v-model="datosEditando.cargo" type="text" placeholder="Opcional" />
                  </label>
                </div>

                <div class="permisos__seccion">
                  <h3 class="permisos__seccion-titulo"><AuthIcon name="shield-check" /> Acceso al panel</h3>

                  <div v-if="usuarioEditando && rolPrincipal(usuarioEditando) === 'ADMIN'" class="permisos__admin-total">
                    <span class="permisos__admin-total-icono"><AuthIcon name="shield" /></span>
                    <div>
                      <strong>Administrador</strong>
                      <p>Ve y gestiona todas las vistas del panel — no se otorgan permisos uno por uno.</p>
                    </div>
                  </div>

                  <template v-else>
                    <p class="eca-ayuda permisos__ayuda-vistas">Prende cada vista a la que este usuario debe poder entrar en el panel.</p>

                    <div v-for="vista in vistasConPermisos" :key="vista.clave" class="permisos__vista" :class="{ 'permisos__vista--activa': vistaEncendida(vista) }">
                      <div class="permisos__vista-fila">
                        <span class="permisos__vista-icono"><AuthIcon :name="vista.icono" /></span>
                        <span class="permisos__vista-etiqueta">{{ vista.etiqueta }}</span>
                        <label class="permisos__switch">
                          <input
                            type="checkbox"
                            :checked="vistaEncendida(vista)"
                            @change="alternarVista(vista)"
                          />
                          <span class="permisos__switch-riel"></span>
                        </label>
                      </div>

                      <Transition name="permisos-subpermisos">
                        <div v-if="vista.subPermisos.length && vistaEncendida(vista)" class="permisos__subpermisos">
                          <label v-for="p in vista.subPermisos" :key="p.clave" class="permisos__item">
                            <input
                              type="checkbox"
                              :checked="permisosSeleccionados.has(p.clave)"
                              @change="alternarPermiso(p.clave)"
                            />
                            <span>{{ p.nombre }}</span>
                          </label>
                        </div>
                      </Transition>
                    </div>
                  </template>
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
.permisos__accion--editar {
  background: linear-gradient(135deg, var(--eca-green-600), var(--eca-green-500));
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
  flex: 1;
  margin: 0;
}
.permisos__password-fila {
  display: flex;
  align-items: stretch;
  gap: 0.5rem;
}
.permisos__copiar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0 1rem;
  border-radius: var(--eca-r-sm);
  border: 1.5px solid var(--eca-green-600);
  background: #fff;
  color: var(--eca-green-700);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s ease;
}
.permisos__copiar svg {
  width: 0.95rem;
  height: 0.95rem;
}
.permisos__copiar:hover {
  background: #f0fdf4;
  transform: translateY(-1px);
}
.permisos__copiar--hecho {
  background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700));
  border-color: transparent;
  color: #fff;
}
.permisos-copiar-icono-enter-active,
.permisos-copiar-icono-leave-active {
  transition: opacity 0.2s ease, transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.permisos-copiar-icono-enter-from {
  opacity: 0;
  transform: scale(0.5) rotate(-20deg);
}
.permisos-copiar-icono-leave-to {
  opacity: 0;
  transform: scale(0.6);
}
.permisos__icono-exito {
  animation: permisosExitoResorte 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes permisosExitoResorte {
  0% { transform: scale(0.3); opacity: 0; }
  60% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(1); }
}

.permisos__modal-cuerpo {
  padding: 1.25rem 1.75rem;
}
.permisos__seccion {
  margin-bottom: 1.5rem;
}
.permisos__seccion:last-child {
  margin-bottom: 0;
}
.permisos__seccion-titulo {
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--eca-purple-700);
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--eca-surface-border);
}
.permisos__seccion-titulo {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}
.permisos__seccion-titulo svg {
  width: 0.85rem;
  height: 0.85rem;
}
.permisos__campos-fila {
  display: flex;
  gap: 0.9rem;
}
.permisos__campo {
  display: flex;
  flex-direction: column;
  gap: 0.32rem;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--eca-ink-soft);
  flex: 1;
  margin-bottom: 0.85rem;
}
.permisos__campo input {
  padding: 0.65rem 0.85rem;
  border-radius: var(--eca-r-sm);
  border: 1.5px solid var(--eca-surface-border);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--eca-ink);
  background: var(--eca-surface);
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.permisos__campo input:focus {
  outline: none;
  border-color: var(--eca-green-500);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14);
}
.permisos__ayuda-vistas {
  margin: -0.3rem 0 0.85rem;
}
.permisos__admin-total {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1rem 1.1rem;
  border-radius: var(--eca-r-md);
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
}
.permisos__admin-total-icono {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3);
}
.permisos__admin-total-icono svg {
  width: 1.15rem;
  height: 1.15rem;
}
.permisos__admin-total strong {
  display: block;
  font-size: 0.92rem;
  color: #92400e;
  margin-bottom: 0.15rem;
}
.permisos__admin-total p {
  margin: 0;
  font-size: 0.8rem;
  color: #92400e;
  opacity: 0.85;
  line-height: 1.4;
}
.permisos__vista {
  border: 1.5px solid var(--eca-surface-border);
  border-radius: var(--eca-r-md);
  padding: 0.75rem 0.95rem;
  margin-bottom: 0.55rem;
  background: var(--eca-surface);
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.permisos__vista--activa {
  border-color: rgba(34, 197, 94, 0.4);
  background: #fff;
  box-shadow: 0 2px 10px rgba(34, 197, 94, 0.08);
}
.permisos__vista-fila {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.permisos__vista-icono {
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 50%;
  background: #fff;
  border: 1px solid var(--eca-surface-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--eca-ink-soft);
  transition: color 0.2s ease, border-color 0.2s ease;
}
.permisos__vista--activa .permisos__vista-icono {
  color: var(--eca-green-700);
  border-color: rgba(34, 197, 94, 0.4);
}
.permisos__vista-icono svg {
  width: 0.95rem;
  height: 0.95rem;
}
.permisos__vista-etiqueta {
  flex: 1;
  font-weight: 700;
  font-size: 0.88rem;
  color: var(--eca-ink);
}
.permisos__subpermisos {
  margin: 0.65rem 0 0 2.7rem;
  padding-top: 0.55rem;
  border-top: 1px dashed var(--eca-surface-border);
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.permisos-subpermisos-enter-active,
.permisos-subpermisos-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
  overflow: hidden;
}
.permisos-subpermisos-enter-from,
.permisos-subpermisos-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Switch tipo "pill" — mismo lenguaje visual que `.geografia__switch`
   (GeografiaView.vue), generalizado aquí para las vistas del panel. */
.permisos__switch {
  position: relative;
  width: 2.5rem;
  height: 1.4rem;
  flex-shrink: 0;
  cursor: pointer;
}
.permisos__switch input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}
.permisos__switch-riel {
  position: absolute;
  inset: 0;
  background: #d1d5db;
  border-radius: 999px;
  transition: background 0.2s ease;
}
.permisos__switch-riel::before {
  content: '';
  position: absolute;
  width: 1.1rem;
  height: 1.1rem;
  left: 0.15rem;
  top: 50%;
  transform: translate(0, -50%);
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform 0.2s ease;
}
.permisos__switch input:checked + .permisos__switch-riel {
  background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700));
}
.permisos__switch input:checked + .permisos__switch-riel::before {
  transform: translate(1.1rem, -50%);
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

/* Campo con botón ojo (contraseña) */
.permisos__campo-ojo {
  position: relative;
  display: flex;
  align-items: center;
}
.permisos__campo-ojo input {
  flex: 1;
  padding-right: 2.6rem;
}
.permisos__campo-ojo--con-match input {
  padding-right: 4rem;
}
.permisos__ojo {
  position: absolute;
  right: 0.6rem;
  background: none;
  border: none;
  color: var(--eca-ink-soft);
  cursor: pointer;
  padding: 0.2rem;
  display: flex;
  align-items: center;
  opacity: 0.6;
  transition: opacity 0.15s;
}
.permisos__ojo:hover { opacity: 1; }
.permisos__ojo svg { width: 1rem; height: 1rem; }

/* Barra de fuerza */
.permisos__fuerza {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 0.4rem;
}
.permisos__fuerza-barras {
  display: flex;
  gap: 0.25rem;
  flex: 1;
}
.permisos__fuerza-barra {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: var(--eca-surface-border);
  transition: background 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.permisos__fuerza-etiqueta {
  font-size: 0.75rem;
  font-weight: 700;
  min-width: 4.5rem;
  text-align: right;
  transition: color 0.3s ease;
}

/* Input con estado ok/error */
.permisos__input--ok {
  border-color: #22c55e !important;
  background: #f0fdf4 !important;
}
.permisos__input--error {
  border-color: #ef4444 !important;
  background: #fef2f2 !important;
}

/* Icono match dentro del campo — va a la derecha del botón ojo */
.permisos__campo-ojo--con-match .permisos__ojo { right: 2rem; }
.permisos__match-icono {
  position: absolute;
  right: 0.5rem;
  display: flex;
  align-items: center;
  pointer-events: none;
}
.permisos__match-icono svg { width: 1rem; height: 1rem; }
.permisos__match-icono--ok { color: #22c55e; }
.permisos__match-icono--no { color: #ef4444; }

/* Hint de error bajo el campo */
.permisos__campo-hint {
  font-size: 0.75rem;
  font-weight: 600;
  margin: 0.25rem 0 0;
}
.permisos__campo-hint--error { color: #ef4444; }

/* Select rol en formulario crear */
.permisos__select-crear-rol {
  padding: 0.65rem 0.85rem;
  border-radius: var(--eca-r-sm);
  border: 1.5px solid var(--eca-surface-border);
  font: inherit;
  font-size: 0.9rem;
  background: var(--eca-surface);
  color: var(--eca-ink);
}

/* Éxito: tarjeta con info del usuario */
.permisos__exito-info {
  background: var(--eca-surface);
  border: 1px solid var(--eca-surface-border);
  border-radius: var(--eca-r-md);
  padding: 1rem 1.1rem;
}
.permisos__exito-fila {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.permisos__exito-icono {
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.permisos__exito-icono svg { width: 1rem; height: 1rem; }
.permisos__exito-fila strong { display: block; font-size: 0.9rem; }
.permisos__exito-fila span { font-size: 0.8rem; color: var(--eca-ink-soft); }

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
  .permisos__form-fila,
  .permisos__campos-fila {
    flex-direction: column;
    gap: 0;
  }
  .permisos__nuevo {
    margin-left: 0;
    width: 100%;
  }
}
</style>
