<!-- admin-eca — vista "Notificaciones": el admin redacta, programa y envía avisos
     a los técnicos de la app (todos o uno), con imágenes/videos/enlace, y ve el
     historial con cuántos ya lo leyeron. Mismo lenguaje que Asistencia/Actividades
     (header verde, panel fusionado, tabla con scroll interno, modales con blur).
     TODAS las horas se capturan y muestran en horario de la Ciudad de México. -->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import AuthIcon from '../components/auth/AuthIcon.vue'
import { useAuthStore } from '../stores/auth'
import {
  listarNotificaciones,
  crearNotificacion,
  retirarNotificacion,
  buscarDestinatarios,
  subirMedio,
  MAX_VIDEO,
  MAX_IMAGEN,
} from '../services/notificacionesService'

const auth = useAuthStore()
const puedeEnviar = computed(() => auth.tienePermiso('notificaciones.enviar'))
const puedeRetirar = computed(() => auth.tienePermiso('notificaciones.retirar'))

const API = import.meta.env.VITE_API_URL || ''
const ZONA = 'America/Mexico_City'

const TIPOS = [
  { clave: 'INFO', etiqueta: 'Informativa', color: '#2563eb' },
  { clave: 'EXITO', etiqueta: 'Éxito', color: '#16a34a' },
  { clave: 'ALERTA', etiqueta: 'Alerta', color: '#d97706' },
  { clave: 'URGENTE', etiqueta: 'Urgente', color: '#dc2626' },
]
const COLOR_TIPO = Object.fromEntries(TIPOS.map((t) => [t.clave, t.color]))
const ETIQUETA_TIPO = Object.fromEntries(TIPOS.map((t) => [t.clave, t.etiqueta]))

// ------------------------------------------------------------ tiempo (CDMX)
const fmtFechaHora = new Intl.DateTimeFormat('es-MX', {
  timeZone: ZONA, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true,
})
function formatear(iso) {
  return iso ? fmtFechaHora.format(new Date(iso)) : null
}
// "YYYY-MM-DDTHH:mm" de la hora actual en CDMX (mínimo de los datetime-local).
function ahoraCdmxLocal(masMinutos = 0) {
  const d = new Date(Date.now() + masMinutos * 60000)
  const p = Object.fromEntries(
    new Intl.DateTimeFormat('en-CA', {
      timeZone: ZONA, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(d).map((x) => [x.type, x.value]),
  )
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`
}

// ----------------------------------------------------------------- listado
const cargando = ref(false)
const error = ref('')
const items = ref([])
const filtroTexto = ref('')
const filtroEstado = ref('')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    items.value = await listarNotificaciones({ estado: filtroEstado.value || undefined, texto: filtroTexto.value || undefined })
  } catch {
    error.value = 'No se pudo cargar el historial de notificaciones.'
  } finally {
    cargando.value = false
  }
}
let temporizadorBusqueda = null
watch(filtroTexto, () => {
  clearTimeout(temporizadorBusqueda)
  temporizadorBusqueda = setTimeout(cargar, 300)
})

const stats = computed(() => {
  const publicadas = items.value.filter((n) => n.estado === 'PUBLICADA')
  const leidas = publicadas.reduce((s, n) => s + n.leidas, 0)
  const alcance = publicadas.reduce((s, n) => s + (n.destinatarios_total || 0), 0)
  return {
    total: items.value.length,
    programadas: items.value.filter((n) => n.estado === 'PROGRAMADA').length,
    vigentes: publicadas.filter((n) => n.vigente).length,
    lectura: alcance ? Math.round((leidas / alcance) * 100) : 0,
  }
})

function estadoVisible(n) {
  if (n.estado === 'PROGRAMADA') return { texto: 'Programada', clase: 'eca-badge--azul' }
  if (n.estado === 'RETIRADA') return { texto: 'Retirada', clase: 'eca-badge--gris' }
  if (!n.vigente) return { texto: 'Vencida', clase: 'eca-badge--ambar' }
  return { texto: 'Publicada', clase: 'eca-badge--verde' }
}
function urlMedio(a) {
  return `${API}${a.url}`
}
function porcentajeLectura(n) {
  return n.destinatarios_total ? Math.round((n.leidas / n.destinatarios_total) * 100) : 0
}

// -------------------------------------------------------------- compositor
const compositorAbierto = ref(false)
const paso = ref('editar') // 'editar' | 'confirmar'
const enviando = ref(false)
const errorCompositor = ref('')

const vacio = () => ({
  titulo: '', subtitulo: '', descripcion: '', url: '', url_texto: '', tipo: 'INFO',
  destino: 'TODOS', usuario: null,
  modoEnvio: 'AHORA', programada: '',
  modoVigencia: 'INDEFINIDA', expira: '',
})
const f = ref(vacio())
const archivos = ref([]) // { id, nombre, tipo, previa, progreso, estado, uuid, error }

// Buscador de técnico (destinatario único)
const busqueda = ref('')
const sugerencias = ref([])
const mostrarSugerencias = ref(false)
const buscando = ref(false)
let temporizadorDest = null
let secuenciaBusqueda = 0
async function ejecutarBusqueda() {
  const mi = ++secuenciaBusqueda
  buscando.value = true
  try {
    const r = await buscarDestinatarios(busqueda.value.trim() || undefined)
    if (mi === secuenciaBusqueda) sugerencias.value = r
  } catch {
    if (mi === secuenciaBusqueda) sugerencias.value = []
  } finally {
    if (mi === secuenciaBusqueda) buscando.value = false
  }
}
watch(busqueda, () => {
  if (f.value.usuario) return
  clearTimeout(temporizadorDest)
  temporizadorDest = setTimeout(ejecutarBusqueda, 250)
})
function elegirDestinatario(u) {
  f.value.usuario = u
  busqueda.value = u.nombre
  mostrarSugerencias.value = false
}
function quitarDestinatario() {
  f.value.usuario = null
  busqueda.value = ''
  ejecutarBusqueda()
}
function iniciales(nombre) {
  const p = (nombre || '').trim().split(/\s+/)
  return ((p[0]?.[0] || '') + (p[1]?.[0] || '')).toUpperCase() || '??'
}

function abrirCompositor() {
  f.value = vacio()
  archivos.value.forEach((a) => a.previa && URL.revokeObjectURL(a.previa))
  archivos.value = []
  busqueda.value = ''
  sugerencias.value = []
  errorCompositor.value = ''
  paso.value = 'editar'
  compositorAbierto.value = true
}
function cerrarCompositor() {
  if (enviando.value) return
  compositorAbierto.value = false
}

// Adjuntos
const entrada = ref(null)
const arrastrando = ref(false)
let contadorArchivos = 0
async function agregarArchivos(lista) {
  for (const archivo of Array.from(lista)) {
    const esVideo = archivo.type.startsWith('video/')
    const esImagen = archivo.type.startsWith('image/')
    const id = ++contadorArchivos
    const item = {
      id, nombre: archivo.name, tipo: esVideo ? 'VIDEO' : 'IMAGEN',
      previa: esImagen || esVideo ? URL.createObjectURL(archivo) : null,
      tamano: archivo.size, progreso: 0, estado: 'subiendo', uuid: null, error: '',
    }
    archivos.value.push(item)
    const ref_ = archivos.value[archivos.value.length - 1]
    if (!esVideo && !esImagen) {
      ref_.estado = 'error'
      ref_.error = 'Solo se permiten imágenes y videos.'
      continue
    }
    if (esVideo && archivo.size > MAX_VIDEO) {
      ref_.estado = 'error'
      ref_.error = 'El video supera el máximo de 200 MB.'
      continue
    }
    if (esImagen && archivo.size > MAX_IMAGEN) {
      ref_.estado = 'error'
      ref_.error = 'La imagen supera el máximo de 25 MB.'
      continue
    }
    subirMedio(archivo, (p) => (ref_.progreso = p))
      .then((adj) => {
        ref_.uuid = adj.uuid
        ref_.progreso = 1
        ref_.estado = 'listo'
      })
      .catch((e) => {
        ref_.estado = 'error'
        ref_.error = e.response?.data?.detail || e.response?.data?.mensaje || 'No se pudo subir el archivo.'
      })
  }
}
function alElegir(e) {
  agregarArchivos(e.target.files)
  e.target.value = ''
}
function alSoltar(e) {
  arrastrando.value = false
  agregarArchivos(e.dataTransfer.files)
}
function quitarArchivo(a) {
  if (a.previa) URL.revokeObjectURL(a.previa)
  archivos.value = archivos.value.filter((x) => x.id !== a.id)
}
const subiendoAlgo = computed(() => archivos.value.some((a) => a.estado === 'subiendo'))
function tamanoLegible(b) {
  return b >= 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`
}

// Validación y envío
const problemas = computed(() => {
  const p = []
  const d = f.value
  if (!d.titulo.trim()) p.push('Escribe un título.')
  if (d.destino === 'USUARIO' && !d.usuario) p.push('Elige al técnico destinatario.')
  if (d.url.trim() && !/^(https:\/\/|\/(?!\/))/.test(d.url.trim())) p.push('La URL debe empezar con https:// o con /.')
  if (d.modoEnvio === 'PROGRAMADA') {
    if (!d.programada) p.push('Elige la fecha y hora de envío.')
    else if (d.programada <= ahoraCdmxLocal()) p.push('La hora programada debe ser futura (hora CDMX).')
  }
  if (d.modoVigencia === 'FECHA') {
    const inicio = d.modoEnvio === 'PROGRAMADA' && d.programada ? d.programada : ahoraCdmxLocal()
    if (!d.expira) p.push('Elige cuándo se elimina la notificación.')
    else if (d.expira <= inicio) p.push('La fecha de eliminación debe ser posterior a la de envío.')
  }
  if (subiendoAlgo.value) p.push('Espera a que terminen de subir los archivos.')
  if (archivos.value.some((a) => a.estado === 'error')) p.push('Quita los archivos con error.')
  return p
})

function pasarAConfirmar() {
  errorCompositor.value = ''
  if (problemas.value.length) {
    errorCompositor.value = problemas.value[0]
    return
  }
  paso.value = 'confirmar'
}

async function enviar() {
  enviando.value = true
  errorCompositor.value = ''
  const d = f.value
  try {
    await crearNotificacion({
      titulo: d.titulo.trim(),
      subtitulo: d.subtitulo.trim() || null,
      descripcion: d.descripcion.trim() || null,
      url: d.url.trim() || null,
      url_texto: d.url_texto.trim() || null,
      tipo: d.tipo,
      destino: d.destino,
      usuario_destino_id: d.destino === 'USUARIO' ? d.usuario.id : null,
      // Sin zona horaria a propósito: el servidor las interpreta como CDMX.
      programada_para: d.modoEnvio === 'PROGRAMADA' ? `${d.programada}:00` : null,
      expira_en: d.modoVigencia === 'FECHA' ? `${d.expira}:00` : null,
      adjuntos: archivos.value.filter((a) => a.estado === 'listo').map((a) => a.uuid),
    })
    compositorAbierto.value = false
    mensajeExito.value = d.modoEnvio === 'PROGRAMADA' ? 'Notificación programada.' : 'Notificación enviada.'
    setTimeout(() => (mensajeExito.value = ''), 3500)
    await cargar()
  } catch (e) {
    errorCompositor.value = e.response?.data?.detail || e.response?.data?.mensaje || 'No se pudo enviar la notificación.'
    paso.value = 'editar'
  } finally {
    enviando.value = false
  }
}
const mensajeExito = ref('')

const resumenEnvio = computed(() => {
  const d = f.value
  const para = d.destino === 'TODOS' ? 'todos los técnicos' : d.usuario?.nombre
  const cuando = d.modoEnvio === 'AHORA' ? 'ahora mismo' : `el ${fmtLocal(d.programada)} (hora CDMX)`
  const hasta = d.modoVigencia === 'INDEFINIDA' ? 'Se conserva indefinidamente.' : `Se elimina el ${fmtLocal(d.expira)} (hora CDMX).`
  return { para, cuando, hasta }
})
function fmtLocal(valor) {
  if (!valor) return ''
  const [fecha, hora] = valor.split('T')
  const [a, m, di] = fecha.split('-').map(Number)
  const [h, mi] = hora.split(':').map(Number)
  return new Date(a, m - 1, di, h, mi).toLocaleString('es-MX', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true,
  })
}

// ---------------------------------------------------------------- detalle
const detalle = ref(null)
const retirando = ref(null)
const retirandoCargando = ref(false)
async function confirmarRetiro() {
  retirandoCargando.value = true
  try {
    await retirarNotificacion(retirando.value.uuid)
    retirando.value = null
    detalle.value = null
    await cargar()
  } catch (e) {
    error.value = e.response?.data?.detail || 'No se pudo retirar la notificación.'
    retirando.value = null
  } finally {
    retirandoCargando.value = false
  }
}

// Refresco periódico: las programadas pasan a publicadas y suben las lecturas.
let intervalo = null
onMounted(() => {
  cargar()
  intervalo = setInterval(() => {
    if (!compositorAbierto.value) cargar()
  }, 30000)
})
onBeforeUnmount(() => {
  clearInterval(intervalo)
  clearTimeout(temporizadorBusqueda)
  clearTimeout(temporizadorDest)
  archivos.value.forEach((a) => a.previa && URL.revokeObjectURL(a.previa))
})
</script>

<template>
  <section class="notif-vista">
    <div class="eca-page-header">
      <span class="eca-page-header__icono"><AuthIcon name="bell" /></span>
      <div class="eca-page-header__texto">
        <h1>Notificaciones</h1>
        <p>Envía avisos a los técnicos de la app: al instante o programados.</p>
      </div>
      <button v-if="puedeEnviar" type="button" class="notif-nueva" @click="abrirCompositor">
        <AuthIcon name="plus" /> <span>Nueva notificación</span>
      </button>
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
      <Transition name="notif-toast">
        <p v-if="mensajeExito" class="notif-exito" role="status"><AuthIcon name="check-circle" /> {{ mensajeExito }}</p>
      </Transition>

      <div class="notif__stats">
        <div class="eca-stat-card eca-stat-card--morado">
          <span class="eca-stat-card__icono"><AuthIcon name="bell" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.total }}</div><div class="eca-stat-card__etiqueta">Notificaciones</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--azul">
          <span class="eca-stat-card__icono"><AuthIcon name="calendar" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.programadas }}</div><div class="eca-stat-card__etiqueta">Programadas</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--verde">
          <span class="eca-stat-card__icono"><AuthIcon name="check-circle" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.vigentes }}</div><div class="eca-stat-card__etiqueta">Vigentes</div></div>
        </div>
        <div class="eca-stat-card eca-stat-card--ambar">
          <span class="eca-stat-card__icono"><AuthIcon name="eye" /></span>
          <div><div class="eca-stat-card__valor">{{ stats.lectura }}%</div><div class="eca-stat-card__etiqueta">Leídas (promedio)</div></div>
        </div>
      </div>

      <div class="notif__filtros">
        <div class="notif__buscador">
          <span class="notif__buscador-icono"><AuthIcon name="search" /></span>
          <input v-model="filtroTexto" type="text" placeholder="Buscar por título…" />
        </div>
        <select v-model="filtroEstado" class="notif__select" @change="cargar">
          <option value="">Todos los estados</option>
          <option value="PUBLICADA">Publicadas</option>
          <option value="PROGRAMADA">Programadas</option>
          <option value="RETIRADA">Retiradas</option>
        </select>
      </div>
    </div>

    <div class="eca-card notif__cuerpo">
      <p v-if="cargando && !items.length" class="eca-ayuda">Cargando…</p>
      <div v-else-if="!items.length" class="eca-vacio">
        <AuthIcon name="bell" />
        <p>Aún no hay notificaciones con estos filtros.</p>
      </div>
      <div v-else class="notif__tabla-contenedor">
        <table class="eca-tabla notif__tabla">
          <thead>
            <tr>
              <th>Notificación</th>
              <th>Destino</th>
              <th>Publicación</th>
              <th>Se elimina</th>
              <th>Lecturas</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="n in items" :key="n.uuid">
              <td>
                <div class="notif__celda-titulo">
                  <span class="notif__tipo-punto" :style="{ background: COLOR_TIPO[n.tipo] }" :title="ETIQUETA_TIPO[n.tipo]"></span>
                  <div class="notif__celda-texto">
                    <strong>{{ n.titulo }}</strong>
                    <small v-if="n.subtitulo">{{ n.subtitulo }}</small>
                    <span v-if="n.adjuntos.length" class="notif__adjuntos-mini">
                      <AuthIcon name="image" /> {{ n.adjuntos.length }}
                    </span>
                  </div>
                </div>
              </td>
              <td>
                <span v-if="n.destino === 'TODOS'" class="eca-badge eca-badge--morado">Todos los técnicos</span>
                <span v-else class="notif__destinatario">{{ n.destinatario || 'Técnico' }}</span>
              </td>
              <td>{{ formatear(n.estado === 'PROGRAMADA' ? n.programada_para : n.publicada_en) || '—' }}</td>
              <td>{{ n.expira_en ? formatear(n.expira_en) : 'Indefinida' }}</td>
              <td>
                <div v-if="n.estado === 'PUBLICADA'" class="notif__lecturas">
                  <div class="notif__barra"><span :style="{ width: porcentajeLectura(n) + '%' }"></span></div>
                  <small>{{ n.leidas }} / {{ n.destinatarios_total ?? 0 }}</small>
                </div>
                <span v-else class="notif__nada">—</span>
              </td>
              <td><span class="eca-badge" :class="estadoVisible(n).clase">{{ estadoVisible(n).texto }}</span></td>
              <td>
                <div class="notif__acciones">
                  <button type="button" class="notif__accion notif__accion--detalle" title="Ver detalles" @click="detalle = n">
                    <AuthIcon name="clipboard" />
                  </button>
                  <button
                    v-if="puedeRetirar && n.estado !== 'RETIRADA'"
                    type="button"
                    class="notif__accion notif__accion--retirar"
                    title="Retirar"
                    @click="retirando = n"
                  >
                    <AuthIcon name="trash" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ===================== Compositor ===================== -->
    <Teleport to="body">
      <Transition name="notif-fondo">
        <div v-if="compositorAbierto" class="notif-modal__fondo" @click.self="cerrarCompositor">
          <Transition name="notif-tarjeta" appear>
            <div class="notif-compositor" role="dialog" aria-modal="true">
              <header class="notif-compositor__cab">
                <span class="notif-compositor__icono"><AuthIcon name="send" /></span>
                <div>
                  <h2>{{ paso === 'editar' ? 'Nueva notificación' : 'Confirma el envío' }}</h2>
                  <p>{{ paso === 'editar' ? 'Todo en horario de la Ciudad de México.' : 'Revisa antes de enviar.' }}</p>
                </div>
                <button type="button" class="notif-cerrar" aria-label="Cerrar" @click="cerrarCompositor"><AuthIcon name="close" /></button>
              </header>

              <div v-show="paso === 'editar'" class="notif-compositor__cuerpo">
                <div class="notif-form">
                  <p v-if="errorCompositor" class="eca-alerta-error" role="alert">{{ errorCompositor }}</p>

                  <label class="notif-campo">
                    <span>Título <em>*</em></span>
                    <input v-model="f.titulo" type="text" maxlength="160" placeholder="Ej. Nueva capacitación disponible" />
                  </label>
                  <label class="notif-campo">
                    <span>Subtítulo</span>
                    <input v-model="f.subtitulo" type="text" maxlength="200" placeholder="Una línea que complemente el título" />
                  </label>
                  <label class="notif-campo">
                    <span>Descripción</span>
                    <textarea v-model="f.descripcion" rows="4" maxlength="5000" placeholder="Escribe aquí el detalle del aviso…"></textarea>
                  </label>

                  <div class="notif-campo">
                    <span>Tipo</span>
                    <div class="notif-tipos">
                      <button
                        v-for="t in TIPOS" :key="t.clave" type="button" class="notif-tipo"
                        :class="{ 'notif-tipo--activo': f.tipo === t.clave }"
                        :style="{ '--c': t.color }" @click="f.tipo = t.clave"
                      ><i></i>{{ t.etiqueta }}</button>
                    </div>
                  </div>

                  <div class="notif-campo-fila">
                    <label class="notif-campo">
                      <span><AuthIcon name="link" /> Enlace (opcional)</span>
                      <input v-model="f.url" type="text" placeholder="https://…" />
                    </label>
                    <label class="notif-campo">
                      <span>Texto del botón</span>
                      <input v-model="f.url_texto" type="text" maxlength="60" placeholder="Ver más" />
                    </label>
                  </div>

                  <!-- Adjuntos -->
                  <div class="notif-campo">
                    <span>Imágenes y videos <small>(imagen hasta 25 MB · video hasta 200 MB)</small></span>
                    <div
                      class="notif-drop" :class="{ 'notif-drop--activo': arrastrando }"
                      @dragover.prevent="arrastrando = true" @dragleave.prevent="arrastrando = false" @drop.prevent="alSoltar"
                      @click="entrada.click()"
                    >
                      <AuthIcon name="image" />
                      <p><strong>Arrastra archivos</strong> o toca para elegir</p>
                      <input ref="entrada" type="file" accept="image/*,video/*" multiple hidden @change="alElegir" />
                    </div>
                    <TransitionGroup name="notif-lista" tag="ul" class="notif-archivos">
                      <li v-for="a in archivos" :key="a.id" :class="{ 'notif-archivo--error': a.estado === 'error' }">
                        <div class="notif-archivo__previa">
                          <video v-if="a.tipo === 'VIDEO' && a.previa" :src="a.previa" muted preload="metadata"></video>
                          <img v-else-if="a.previa" :src="a.previa" alt="" />
                          <AuthIcon v-else name="image" />
                        </div>
                        <div class="notif-archivo__info">
                          <strong>{{ a.nombre }}</strong>
                          <small v-if="a.estado === 'error'">{{ a.error }}</small>
                          <small v-else>{{ a.tipo === 'VIDEO' ? 'Video' : 'Imagen' }} · {{ tamanoLegible(a.tamano) }}<template v-if="a.estado === 'listo'"> · listo</template></small>
                          <div v-if="a.estado === 'subiendo'" class="notif__barra"><span :style="{ width: Math.round(a.progreso * 100) + '%' }"></span></div>
                        </div>
                        <button type="button" class="notif-archivo__quitar" aria-label="Quitar" @click="quitarArchivo(a)"><AuthIcon name="close" /></button>
                      </li>
                    </TransitionGroup>
                  </div>

                  <!-- Destino -->
                  <div class="notif-campo">
                    <span>Destinatarios</span>
                    <div class="notif-segmento">
                      <button type="button" :class="{ 'notif-segmento--activo': f.destino === 'TODOS' }" @click="f.destino = 'TODOS'">Todos los técnicos</button>
                      <button type="button" :class="{ 'notif-segmento--activo': f.destino === 'USUARIO' }" @click="f.destino = 'USUARIO'; ejecutarBusqueda()">Un técnico</button>
                    </div>
                    <div v-if="f.destino === 'USUARIO'" class="notif-dest">
                      <div v-if="f.usuario" class="notif-dest__elegido">
                        <span class="notif-avatar">{{ iniciales(f.usuario.nombre) }}</span>
                        <span class="notif-dest__texto"><strong>{{ f.usuario.nombre }}</strong><small>{{ f.usuario.correo }}</small></span>
                        <button type="button" aria-label="Cambiar" @click="quitarDestinatario"><AuthIcon name="close" /></button>
                      </div>
                      <div v-else class="notif__buscador">
                        <span class="notif__buscador-icono"><AuthIcon name="search" /></span>
                        <input
                          v-model="busqueda" type="text" placeholder="Buscar técnico por nombre, correo o CURP…"
                          @focus="mostrarSugerencias = true; ejecutarBusqueda()" @blur="() => setTimeout(() => (mostrarSugerencias = false), 150)"
                        />
                        <Transition name="notif-toast">
                          <div v-if="mostrarSugerencias" class="notif__sugerencias">
                            <p v-if="buscando && !sugerencias.length" class="notif__sug-vacio">Buscando…</p>
                            <p v-else-if="!sugerencias.length" class="notif__sug-vacio">Sin resultados.</p>
                            <button v-for="u in sugerencias" :key="u.id" type="button" @mousedown.prevent="elegirDestinatario(u)">
                              <span class="notif-avatar">{{ iniciales(u.nombre) }}</span>
                              <span class="notif-dest__texto"><strong>{{ u.nombre }}</strong><small>{{ u.correo }}</small></span>
                            </button>
                          </div>
                        </Transition>
                      </div>
                    </div>
                  </div>

                  <!-- Programación y vigencia -->
                  <div class="notif-campo-fila">
                    <div class="notif-campo">
                      <span><AuthIcon name="send" /> Cuándo enviar</span>
                      <div class="notif-segmento">
                        <button type="button" :class="{ 'notif-segmento--activo': f.modoEnvio === 'AHORA' }" @click="f.modoEnvio = 'AHORA'">Ahora</button>
                        <button type="button" :class="{ 'notif-segmento--activo': f.modoEnvio === 'PROGRAMADA' }" @click="f.modoEnvio = 'PROGRAMADA'; f.programada = f.programada || ahoraCdmxLocal(60)">Programar</button>
                      </div>
                      <input v-if="f.modoEnvio === 'PROGRAMADA'" v-model="f.programada" type="datetime-local" :min="ahoraCdmxLocal()" class="notif-fecha" />
                    </div>
                    <div class="notif-campo">
                      <span><AuthIcon name="calendar" /> Cuándo se elimina</span>
                      <div class="notif-segmento">
                        <button type="button" :class="{ 'notif-segmento--activo': f.modoVigencia === 'INDEFINIDA' }" @click="f.modoVigencia = 'INDEFINIDA'">Indefinido</button>
                        <button type="button" :class="{ 'notif-segmento--activo': f.modoVigencia === 'FECHA' }" @click="f.modoVigencia = 'FECHA'; f.expira = f.expira || ahoraCdmxLocal(60 * 24)">En una fecha</button>
                      </div>
                      <input v-if="f.modoVigencia === 'FECHA'" v-model="f.expira" type="datetime-local" :min="f.programada || ahoraCdmxLocal()" class="notif-fecha" />
                    </div>
                  </div>
                </div>

                <!-- Vista previa en vivo -->
                <aside class="notif-previa">
                  <span class="notif-previa__etiqueta">Vista previa</span>
                  <div class="notif-tarjeta-previa" :style="{ '--c': COLOR_TIPO[f.tipo] }">
                    <div class="notif-tarjeta-previa__lateral"><AuthIcon name="bell" /></div>
                    <div class="notif-tarjeta-previa__cuerpo">
                      <div class="notif-tarjeta-previa__meta"><span>{{ ETIQUETA_TIPO[f.tipo] }}</span><span>ahora</span></div>
                      <strong>{{ f.titulo || 'Título de la notificación' }}</strong>
                      <em v-if="f.subtitulo">{{ f.subtitulo }}</em>
                      <p v-if="f.descripcion">{{ f.descripcion }}</p>
                      <div v-if="archivos.find((a) => a.previa)" class="notif-tarjeta-previa__media">
                        <video v-if="archivos.find((a) => a.previa).tipo === 'VIDEO'" :src="archivos.find((a) => a.previa).previa" muted></video>
                        <img v-else :src="archivos.find((a) => a.previa).previa" alt="" />
                        <span v-if="archivos.length > 1" class="notif-tarjeta-previa__mas">+{{ archivos.length - 1 }}</span>
                      </div>
                      <span v-if="f.url.trim()" class="notif-tarjeta-previa__boton">{{ f.url_texto || 'Ver más' }}</span>
                    </div>
                  </div>
                </aside>
              </div>

              <div v-if="paso === 'confirmar'" class="notif-confirmar">
                <div class="notif-confirmar__icono"><AuthIcon name="send" /></div>
                <h3>Se enviará a <strong>{{ resumenEnvio.para }}</strong></h3>
                <p>Envío: <strong>{{ resumenEnvio.cuando }}</strong>.<br />{{ resumenEnvio.hasta }}</p>
                <div class="notif-tarjeta-previa notif-tarjeta-previa--mini" :style="{ '--c': COLOR_TIPO[f.tipo] }">
                  <div class="notif-tarjeta-previa__lateral"><AuthIcon name="bell" /></div>
                  <div class="notif-tarjeta-previa__cuerpo"><strong>{{ f.titulo }}</strong><em v-if="f.subtitulo">{{ f.subtitulo }}</em></div>
                </div>
              </div>

              <footer class="notif-compositor__pie">
                <template v-if="paso === 'editar'">
                  <button type="button" class="eca-btn eca-btn-secundario" @click="cerrarCompositor">Cancelar</button>
                  <button type="button" class="eca-btn eca-btn-primary" :disabled="subiendoAlgo" @click="pasarAConfirmar">Continuar</button>
                </template>
                <template v-else>
                  <button type="button" class="eca-btn eca-btn-secundario" :disabled="enviando" @click="paso = 'editar'">Volver</button>
                  <button type="button" class="eca-btn eca-btn-primary" :disabled="enviando" @click="enviar">
                    {{ enviando ? 'Enviando…' : f.modoEnvio === 'AHORA' ? 'Enviar ahora' : 'Programar envío' }}
                  </button>
                </template>
              </footer>
            </div>
          </Transition>
        </div>
      </Transition>

      <!-- Detalle -->
      <Transition name="notif-fondo">
        <div v-if="detalle" class="notif-modal__fondo" @click.self="detalle = null">
          <Transition name="notif-tarjeta" appear>
            <div class="notif-detalle" role="dialog" aria-modal="true">
              <button type="button" class="notif-cerrar notif-cerrar--abs" aria-label="Cerrar" @click="detalle = null"><AuthIcon name="close" /></button>
              <div class="notif-detalle__banda" :style="{ background: COLOR_TIPO[detalle.tipo] }"></div>
              <div class="notif-detalle__cuerpo">
                <div class="notif-detalle__etiquetas">
                  <span class="eca-badge" :class="estadoVisible(detalle).clase">{{ estadoVisible(detalle).texto }}</span>
                  <span class="notif-detalle__tipo" :style="{ color: COLOR_TIPO[detalle.tipo] }">{{ ETIQUETA_TIPO[detalle.tipo] }}</span>
                </div>
                <h2>{{ detalle.titulo }}</h2>
                <p v-if="detalle.subtitulo" class="notif-detalle__sub">{{ detalle.subtitulo }}</p>
                <p v-if="detalle.descripcion" class="notif-detalle__desc">{{ detalle.descripcion }}</p>
                <a v-if="detalle.url" :href="detalle.url" target="_blank" rel="noopener" class="notif-detalle__enlace"><AuthIcon name="link" /> {{ detalle.url_texto || detalle.url }}</a>

                <div v-if="detalle.adjuntos.length" class="notif-detalle__media">
                  <template v-for="a in detalle.adjuntos" :key="a.uuid">
                    <video v-if="a.tipo === 'VIDEO'" :src="urlMedio(a)" controls preload="metadata"></video>
                    <a v-else :href="urlMedio(a)" target="_blank" rel="noopener"><img :src="urlMedio(a)" alt="" loading="lazy" /></a>
                  </template>
                </div>

                <dl class="notif-detalle__datos">
                  <div><dt>Destino</dt><dd>{{ detalle.destino === 'TODOS' ? 'Todos los técnicos' : detalle.destinatario }}</dd></div>
                  <div><dt>Enviada por</dt><dd>{{ detalle.creado_por || '—' }}</dd></div>
                  <div v-if="detalle.programada_para"><dt>Programada para</dt><dd>{{ formatear(detalle.programada_para) }}</dd></div>
                  <div><dt>Publicada</dt><dd>{{ formatear(detalle.publicada_en) || 'Aún no' }}</dd></div>
                  <div><dt>Se elimina</dt><dd>{{ detalle.expira_en ? formatear(detalle.expira_en) : 'Indefinida' }}</dd></div>
                  <div><dt>Leída por</dt><dd>{{ detalle.leidas }} de {{ detalle.destinatarios_total ?? 0 }} ({{ porcentajeLectura(detalle) }}%)</dd></div>
                </dl>
                <p class="notif-detalle__nota">Horario de la Ciudad de México.</p>
              </div>
            </div>
          </Transition>
        </div>
      </Transition>

      <!-- Retirar -->
      <Transition name="notif-fondo">
        <div v-if="retirando" class="notif-modal__fondo" @click.self="!retirandoCargando && (retirando = null)">
          <Transition name="notif-tarjeta" appear>
            <div class="notif-retirar" role="alertdialog" aria-modal="true">
              <div class="notif-retirar__icono"><AuthIcon name="trash" /></div>
              <h3>¿Retirar esta notificación?</h3>
              <p><strong>{{ retirando.titulo }}</strong><br />Dejará de mostrarse en la app de los técnicos (el historial se conserva).</p>
              <div class="notif-retirar__acciones">
                <button type="button" class="eca-btn eca-btn-secundario" :disabled="retirandoCargando" @click="retirando = null">Cancelar</button>
                <button type="button" class="notif-retirar__confirmar" :disabled="retirandoCargando" @click="confirmarRetiro">
                  {{ retirandoCargando ? 'Retirando…' : 'Sí, retirar' }}
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
.notif-vista { height: calc(100dvh - 1rem); display: flex; flex-direction: column; min-height: 0; }
.notif-vista > .eca-page-header, .notif-vista > .eca-panel-fusionado { flex-shrink: 0; }
.notif-vista > .notif__cuerpo { flex: 1; min-height: 0; display: flex; flex-direction: column; margin-bottom: 0; padding: 0.75rem 0.9rem; overflow: hidden; }

.notif-nueva {
  display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.5rem 0.95rem; border: none; border-radius: 999px;
  background: #fff; color: var(--eca-green-900, #0f4c26); font-weight: 800; font-size: 0.82rem; font-family: inherit; cursor: pointer;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18); transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.notif-nueva:hover { transform: translateY(-1px) scale(1.04); }
.notif-nueva svg { width: 0.95rem; height: 0.95rem; }
@media (max-width: 560px) { .notif-nueva span { display: none; } .notif-nueva { padding: 0.55rem; } }

.notif-exito { display: flex; align-items: center; gap: 0.45rem; margin: 0 0 0.6rem; padding: 0.55rem 0.8rem; border-radius: var(--eca-r-sm); background: #dcfce7; color: #166534; font-weight: 700; font-size: 0.85rem; }
.notif-exito svg { width: 1rem; height: 1rem; }

.notif__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.55rem; margin-bottom: 0.65rem; }
.notif__stats .eca-stat-card { min-width: 0; padding: 0.45rem 0.65rem; gap: 0.5rem; }
.notif__stats .eca-stat-card :deep(.eca-stat-card__icono) { width: 1.7rem; height: 1.7rem; }
.notif__stats .eca-stat-card :deep(.eca-stat-card__icono svg) { width: 0.85rem; height: 0.85rem; }
.notif__stats .eca-stat-card :deep(.eca-stat-card__valor) { font-size: 0.98rem; }
.notif__stats .eca-stat-card :deep(.eca-stat-card__etiqueta) { font-size: 0.66rem; }
@media (max-width: 820px) { .notif__stats { grid-template-columns: repeat(2, 1fr); } }

.notif__filtros { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.notif__buscador { position: relative; flex: 1 1 14rem; }
.notif__buscador-icono { position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); color: var(--eca-ink-soft); display: flex; pointer-events: none; }
.notif__buscador-icono svg { width: 0.9rem; height: 0.9rem; }
.notif__buscador input { width: 100%; padding: 0.55rem 1rem 0.55rem 2.4rem; border-radius: 999px; border: 1.5px solid #cfe3d5; background: #fff; font-family: inherit; font-size: 0.88rem; box-sizing: border-box; transition: border-color 0.2s, box-shadow 0.2s; }
.notif__buscador input:focus { outline: none; border-color: var(--eca-green-500); box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14); }
.notif__select { height: 2.4rem; padding: 0 0.7rem; border-radius: var(--eca-r-sm); border: 1px solid #cfe3d5; background: #fff; font-family: inherit; font-size: 0.82rem; cursor: pointer; }

.notif__sugerencias { position: absolute; z-index: 30; top: calc(100% + 0.4rem); left: 0; right: 0; background: #fff; border: 1px solid var(--eca-surface-border); border-radius: var(--eca-r-md); box-shadow: 0 12px 32px rgba(0, 0, 0, 0.16); max-height: 15rem; overflow-y: auto; }
.notif__sugerencias button { width: 100%; display: flex; align-items: center; gap: 0.6rem; padding: 0.5rem 0.8rem; border: none; background: none; text-align: left; cursor: pointer; font-family: inherit; }
.notif__sugerencias button:hover { background: var(--eca-surface); }
.notif__sug-vacio { margin: 0; padding: 0.7rem 0.9rem; font-size: 0.8rem; color: var(--eca-ink-soft); }

.notif__tabla-contenedor { flex: 1; min-height: 0; overflow: auto; border-radius: var(--eca-r-md); border: 1px solid var(--eca-surface-border); }
.notif__tabla { min-width: 880px; }
.notif__tabla thead th { position: sticky; top: 0; z-index: 5; background: var(--eca-surface); box-shadow: 0 1px 0 var(--eca-surface-border); }
.notif__celda-titulo { display: flex; align-items: flex-start; gap: 0.6rem; max-width: 22rem; }
.notif__tipo-punto { flex-shrink: 0; width: 0.65rem; height: 0.65rem; border-radius: 50%; margin-top: 0.35rem; box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.05); }
.notif__celda-texto { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.notif__celda-texto strong { font-size: 0.86rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notif__celda-texto small { font-size: 0.74rem; color: var(--eca-ink-soft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notif__adjuntos-mini { display: inline-flex; align-items: center; gap: 0.25rem; font-size: 0.7rem; color: var(--eca-ink-soft); }
.notif__adjuntos-mini svg { width: 0.75rem; height: 0.75rem; }
.notif__destinatario { font-size: 0.82rem; font-weight: 600; }
.notif__nada { color: var(--eca-ink-soft); }
.notif__lecturas { display: flex; flex-direction: column; gap: 0.2rem; min-width: 6.5rem; }
.notif__lecturas small { font-size: 0.72rem; color: var(--eca-ink-soft); }
.notif__barra { height: 0.38rem; border-radius: 99px; background: #e5efe8; overflow: hidden; }
.notif__barra span { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--eca-green-500), #16a34a); transition: width 0.3s ease; }
.notif__acciones { display: flex; gap: 0.4rem; }
.notif__accion { width: 2.1rem; height: 2.1rem; border-radius: 50%; border: none; color: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15); transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); }
.notif__accion:hover { transform: scale(1.1); }
.notif__accion svg { width: 0.95rem; height: 0.95rem; }
.notif__accion--detalle { background: linear-gradient(135deg, #2f7a33, #14501c); }
.notif__accion--retirar { background: linear-gradient(135deg, #8b1a1a, #5c0f0f); }

/* ---- modales ---- */
.notif-modal__fondo { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 1rem; background: rgba(8, 24, 14, 0.5); backdrop-filter: blur(6px); }
.notif-fondo-enter-active, .notif-fondo-leave-active { transition: opacity 0.22s ease; }
.notif-fondo-enter-from, .notif-fondo-leave-to { opacity: 0; }
.notif-tarjeta-enter-active { transition: transform 0.38s cubic-bezier(0.34, 1.4, 0.64, 1), opacity 0.25s ease; }
.notif-tarjeta-leave-active { transition: transform 0.18s ease, opacity 0.18s ease; }
.notif-tarjeta-enter-from, .notif-tarjeta-leave-to { opacity: 0; transform: translateY(18px) scale(0.96); }
.notif-toast-enter-active, .notif-toast-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.notif-toast-enter-from, .notif-toast-leave-to { opacity: 0; transform: translateY(-4px); }
.notif-lista-enter-active, .notif-lista-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.notif-lista-enter-from, .notif-lista-leave-to { opacity: 0; transform: translateX(-10px); }

.notif-compositor { width: 100%; max-width: 980px; max-height: 94dvh; display: flex; flex-direction: column; background: #fff; border-radius: 22px; box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35); overflow: hidden; }
.notif-compositor__cab { display: flex; align-items: center; gap: 0.8rem; padding: 0.95rem 1.2rem; background: linear-gradient(135deg, var(--eca-green-700, #166534), var(--eca-green-900, #0f4c26)); color: #fff; position: relative; }
.notif-compositor__cab h2 { margin: 0; font-size: 1.05rem; }
.notif-compositor__cab p { margin: 0.1rem 0 0; font-size: 0.76rem; opacity: 0.85; }
.notif-compositor__icono { width: 2.4rem; height: 2.4rem; border-radius: 12px; background: rgba(255, 255, 255, 0.16); display: flex; align-items: center; justify-content: center; }
.notif-compositor__icono svg { width: 1.2rem; height: 1.2rem; }
.notif-cerrar { margin-left: auto; width: 2rem; height: 2rem; border-radius: 50%; border: none; background: rgba(255, 255, 255, 0.16); color: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: background 0.15s, transform 0.15s; }
.notif-cerrar:hover { background: rgba(255, 255, 255, 0.28); transform: rotate(90deg); }
.notif-cerrar svg { width: 0.85rem; height: 0.85rem; }
.notif-compositor__cuerpo { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 1.2rem; padding: 1.1rem 1.2rem; overflow-y: auto; flex: 1; min-height: 0; }
@media (max-width: 860px) { .notif-compositor__cuerpo { grid-template-columns: 1fr; } .notif-previa { order: -1; } }
.notif-form { display: flex; flex-direction: column; gap: 0.85rem; min-width: 0; }
.notif-campo { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.notif-campo > span { font-size: 0.74rem; font-weight: 800; color: var(--eca-ink); display: flex; align-items: center; gap: 0.3rem; }
.notif-campo > span svg { width: 0.8rem; height: 0.8rem; }
.notif-campo > span em { color: #dc2626; font-style: normal; }
.notif-campo > span small { font-weight: 500; color: var(--eca-ink-soft); }
.notif-campo input[type='text'], .notif-campo textarea, .notif-fecha { width: 100%; box-sizing: border-box; padding: 0.6rem 0.8rem; border: 1.5px solid #cfe3d5; border-radius: 12px; background: #fff; font-family: inherit; font-size: 0.88rem; resize: vertical; transition: border-color 0.2s, box-shadow 0.2s; }
.notif-campo input:focus, .notif-campo textarea:focus, .notif-fecha:focus { outline: none; border-color: var(--eca-green-500); box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14); }
.notif-campo-fila { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
@media (max-width: 560px) { .notif-campo-fila { grid-template-columns: 1fr; } }

.notif-tipos { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.notif-tipo { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.8rem; border-radius: 999px; border: 1.5px solid #e1e8e3; background: #fff; font-family: inherit; font-size: 0.78rem; font-weight: 700; cursor: pointer; transition: all 0.18s ease; }
.notif-tipo i { width: 0.6rem; height: 0.6rem; border-radius: 50%; background: var(--c); }
.notif-tipo--activo { border-color: var(--c); background: color-mix(in srgb, var(--c) 10%, #fff); color: var(--c); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c) 18%, transparent); }

.notif-drop { display: flex; flex-direction: column; align-items: center; gap: 0.25rem; padding: 0.9rem; border: 2px dashed #b9d4c1; border-radius: 14px; background: #f6fbf7; color: var(--eca-ink-soft); cursor: pointer; text-align: center; transition: all 0.2s ease; }
.notif-drop:hover, .notif-drop--activo { border-color: var(--eca-green-500); background: #eaf8ee; transform: scale(1.01); }
.notif-drop svg { width: 1.4rem; height: 1.4rem; color: var(--eca-green-600, #16a34a); }
.notif-drop p { margin: 0; font-size: 0.8rem; }
.notif-archivos { list-style: none; margin: 0.2rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
.notif-archivos li { display: flex; align-items: center; gap: 0.6rem; padding: 0.4rem 0.5rem; border-radius: 12px; border: 1px solid #e1e8e3; background: #fff; }
.notif-archivo--error { border-color: #fca5a5 !important; background: #fef2f2 !important; }
.notif-archivo__previa { width: 2.8rem; height: 2.8rem; border-radius: 9px; overflow: hidden; background: #eef3ef; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.notif-archivo__previa img, .notif-archivo__previa video { width: 100%; height: 100%; object-fit: cover; }
.notif-archivo__info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.2rem; }
.notif-archivo__info strong { font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notif-archivo__info small { font-size: 0.7rem; color: var(--eca-ink-soft); }
.notif-archivo--error small { color: #b91c1c; }
.notif-archivo__quitar { width: 1.6rem; height: 1.6rem; border-radius: 50%; border: none; background: #eef1ef; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.notif-archivo__quitar svg { width: 0.7rem; height: 0.7rem; }

.notif-segmento { display: inline-flex; align-self: flex-start; padding: 0.2rem; border-radius: 999px; background: #eef3ef; gap: 0.15rem; }
.notif-segmento button { padding: 0.38rem 0.85rem; border: none; border-radius: 999px; background: none; font-family: inherit; font-size: 0.78rem; font-weight: 700; color: var(--eca-ink-soft); cursor: pointer; transition: all 0.2s ease; }
.notif-segmento .notif-segmento--activo { background: #fff; color: var(--eca-green-800, #14501c); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12); }
.notif-dest { margin-top: 0.15rem; }
.notif-dest__elegido { display: flex; align-items: center; gap: 0.6rem; padding: 0.45rem 0.6rem; border-radius: 14px; border: 1.5px solid var(--eca-green-500); background: #f0fbf3; }
.notif-dest__elegido button { margin-left: auto; width: 1.6rem; height: 1.6rem; border-radius: 50%; border: none; background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.notif-dest__elegido button svg { width: 0.7rem; height: 0.7rem; }
.notif-dest__texto { display: flex; flex-direction: column; min-width: 0; }
.notif-dest__texto strong { font-size: 0.84rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notif-dest__texto small { font-size: 0.72rem; color: var(--eca-ink-soft); }
.notif-avatar { flex-shrink: 0; width: 2rem; height: 2rem; border-radius: 50%; background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700)); color: #fff; font-size: 0.72rem; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.notif-fecha { margin-top: 0.1rem; }

/* vista previa */
.notif-previa { display: flex; flex-direction: column; gap: 0.5rem; align-self: start; position: sticky; top: 0; }
.notif-previa__etiqueta { font-size: 0.68rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: var(--eca-ink-soft); }
.notif-tarjeta-previa { display: flex; border-radius: 18px; background: #fff; border: 1px solid #e3ebe5; box-shadow: 0 10px 30px rgba(15, 76, 38, 0.12); overflow: hidden; }
.notif-tarjeta-previa__lateral { width: 3rem; flex-shrink: 0; background: linear-gradient(180deg, var(--c), color-mix(in srgb, var(--c) 70%, #000)); color: #fff; display: flex; justify-content: center; padding-top: 0.9rem; }
.notif-tarjeta-previa__lateral svg { width: 1.2rem; height: 1.2rem; }
.notif-tarjeta-previa__cuerpo { padding: 0.8rem 0.9rem; display: flex; flex-direction: column; gap: 0.3rem; min-width: 0; }
.notif-tarjeta-previa__meta { display: flex; justify-content: space-between; font-size: 0.66rem; font-weight: 800; text-transform: uppercase; color: var(--c); letter-spacing: 0.05em; }
.notif-tarjeta-previa__meta span:last-child { color: var(--eca-ink-soft); font-weight: 600; text-transform: none; }
.notif-tarjeta-previa strong { font-size: 0.92rem; line-height: 1.25; overflow-wrap: anywhere; }
.notif-tarjeta-previa em { font-style: normal; font-size: 0.8rem; color: var(--eca-ink-soft); font-weight: 600; overflow-wrap: anywhere; }
.notif-tarjeta-previa p { margin: 0; font-size: 0.8rem; color: var(--eca-ink); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.notif-tarjeta-previa__media { position: relative; border-radius: 12px; overflow: hidden; margin-top: 0.2rem; background: #000; }
.notif-tarjeta-previa__media img, .notif-tarjeta-previa__media video { width: 100%; max-height: 9rem; object-fit: cover; display: block; }
.notif-tarjeta-previa__mas { position: absolute; right: 0.4rem; bottom: 0.4rem; padding: 0.15rem 0.5rem; border-radius: 99px; background: rgba(0, 0, 0, 0.65); color: #fff; font-size: 0.7rem; font-weight: 800; }
.notif-tarjeta-previa__boton { align-self: flex-start; margin-top: 0.2rem; padding: 0.35rem 0.8rem; border-radius: 99px; background: var(--c); color: #fff; font-size: 0.74rem; font-weight: 800; }
.notif-tarjeta-previa--mini { width: 100%; max-width: 22rem; text-align: left; }

.notif-compositor__pie { display: flex; justify-content: flex-end; gap: 0.6rem; padding: 0.8rem 1.2rem; border-top: 1px solid var(--eca-surface-border); background: #fafcfb; }

.notif-confirmar { padding: 1.6rem 1.4rem; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.6rem; overflow-y: auto; }
.notif-confirmar__icono { width: 3.4rem; height: 3.4rem; border-radius: 50%; background: linear-gradient(135deg, var(--eca-green-500), var(--eca-green-700)); color: #fff; display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 22px rgba(22, 163, 74, 0.35); }
.notif-confirmar__icono svg { width: 1.5rem; height: 1.5rem; }
.notif-confirmar h3 { margin: 0.2rem 0 0; font-size: 1.1rem; }
.notif-confirmar p { margin: 0; font-size: 0.88rem; color: var(--eca-ink-soft); line-height: 1.5; }

/* detalle */
.notif-detalle { position: relative; width: 100%; max-width: 560px; max-height: 92dvh; overflow-y: auto; background: #fff; border-radius: 22px; box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35); }
.notif-cerrar--abs { position: absolute; top: 0.7rem; right: 0.7rem; z-index: 3; background: rgba(0, 0, 0, 0.35); }
.notif-detalle__banda { height: 0.5rem; }
.notif-detalle__cuerpo { padding: 1.2rem 1.3rem 1.3rem; display: flex; flex-direction: column; gap: 0.55rem; }
.notif-detalle__etiquetas { display: flex; align-items: center; gap: 0.5rem; }
.notif-detalle__tipo { font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; }
.notif-detalle h2 { margin: 0.1rem 0 0; font-size: 1.25rem; line-height: 1.25; overflow-wrap: anywhere; }
.notif-detalle__sub { margin: 0; font-weight: 700; color: var(--eca-ink-soft); }
.notif-detalle__desc { margin: 0; white-space: pre-wrap; line-height: 1.5; font-size: 0.9rem; overflow-wrap: anywhere; }
.notif-detalle__enlace { display: inline-flex; align-items: center; gap: 0.4rem; align-self: flex-start; padding: 0.45rem 0.9rem; border-radius: 99px; background: var(--eca-green-600, #16a34a); color: #fff; font-weight: 800; font-size: 0.8rem; text-decoration: none; }
.notif-detalle__enlace svg { width: 0.85rem; height: 0.85rem; }
.notif-detalle__media { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 0.5rem; }
.notif-detalle__media img, .notif-detalle__media video { width: 100%; border-radius: 12px; display: block; max-height: 16rem; object-fit: cover; background: #000; }
.notif-detalle__datos { margin: 0.4rem 0 0; display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem 1rem; padding: 0.9rem; border-radius: 14px; background: #f5faf6; }
.notif-detalle__datos dt { font-size: 0.66rem; font-weight: 800; text-transform: uppercase; color: var(--eca-ink-soft); }
.notif-detalle__datos dd { margin: 0.1rem 0 0; font-size: 0.84rem; font-weight: 600; overflow-wrap: anywhere; }
.notif-detalle__nota { margin: 0; font-size: 0.7rem; color: var(--eca-ink-soft); }
@media (max-width: 480px) { .notif-detalle__datos { grid-template-columns: 1fr; } }

/* retirar */
.notif-retirar { width: 100%; max-width: 400px; background: #fff; border-radius: 22px; padding: 1.5rem; text-align: center; box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35); }
.notif-retirar__icono { width: 3.2rem; height: 3.2rem; margin: 0 auto 0.6rem; border-radius: 50%; background: linear-gradient(135deg, #8b1a1a, #5c0f0f); color: #fff; display: flex; align-items: center; justify-content: center; }
.notif-retirar__icono svg { width: 1.4rem; height: 1.4rem; }
.notif-retirar h3 { margin: 0 0 0.4rem; }
.notif-retirar p { margin: 0 0 1rem; font-size: 0.86rem; color: var(--eca-ink-soft); line-height: 1.5; }
.notif-retirar__acciones { display: flex; gap: 0.6rem; justify-content: center; }
.notif-retirar__confirmar { padding: 0.6rem 1.2rem; border: none; border-radius: 12px; background: linear-gradient(135deg, #8b1a1a, #5c0f0f); color: #fff; font-weight: 800; font-family: inherit; cursor: pointer; }
.notif-retirar__confirmar:disabled { opacity: 0.6; cursor: wait; }
</style>
