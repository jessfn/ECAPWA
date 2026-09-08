<!-- admin-eca — pantalla "Inicio" (pedido explícito): dashboard premium,
     no solo un saludo de una línea. Datos reales (nunca inventados):
     cada tarjeta/sección se pide solo si el usuario tiene el permiso que
     el endpoint exige, y se oculta en silencio si no — igual criterio que
     el resto del panel (nunca un 403 visible por falta de permiso). -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../services/api'
import { listarEcas } from '../services/ecasService'
import { listarActividades } from '../services/actividadesService'
import AuthIcon from '../components/auth/AuthIcon.vue'

const auth = useAuthStore()

const cargando = ref(true)
const stats = ref({ tecnicos: null, activos: null, ecas: null, actividades: null })
const actividadesRecientes = ref([])
const tecnicosPorId = ref(new Map())

const ENLACES = [
  { nombre: 'tecnicos', etiqueta: 'Técnicos', icono: 'user', permiso: 'usuarios.gestionar', color: 'morado' },
  { nombre: 'actividades', etiqueta: 'Actividades', icono: 'clock', permiso: 'actividades.ver_todas', color: 'verde' },
  { nombre: 'ecas', etiqueta: 'ECA', icono: 'school', permiso: 'ecas.ver', color: 'azul' },
  { nombre: 'visor-seguimiento', etiqueta: 'Visor de Seguimiento', icono: 'map-pin', permiso: 'vista.visor_seguimiento', color: 'ambar' },
  { nombre: 'catalogos', etiqueta: 'Catálogos', icono: 'book', permiso: null, color: 'morado' },
  { nombre: 'ambitos', etiqueta: 'Ámbitos', icono: 'shield', permiso: 'ambitos.gestionar', color: 'verde' },
  { nombre: 'asignaciones', etiqueta: 'Asignaciones', icono: 'check-circle', permiso: 'asignaciones.gestionar', color: 'azul' },
]
const enlacesVisibles = computed(() => ENLACES.filter((e) => !e.permiso || auth.tienePermiso(e.permiso)))

const saludo = computed(() => {
  const hora = new Date().getHours()
  if (hora < 12) return 'Buenos días'
  if (hora < 19) return 'Buenas tardes'
  return 'Buenas noches'
})
const fechaHoy = computed(() =>
  new Date().toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
)
function iniciales() {
  const n = (auth.usuario?.nombre || '').trim()
  const a = (auth.usuario?.apellido_paterno || '').trim()
  if (n && a) return (n[0] + a[0]).toUpperCase()
  return n ? n.slice(0, 2).toUpperCase() : 'AD'
}
function rolPrincipal() {
  return auth.usuario?.roles?.[0] || null
}

function iniciales_de(u) {
  const n = (u?.nombre || '').trim()
  const a = (u?.apellido_paterno || '').trim()
  if (n && a) return (n[0] + a[0]).toUpperCase()
  return '??'
}
function tiempoRelativo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const min = Math.round(diffMs / 60000)
  if (min < 1) return 'justo ahora'
  if (min < 60) return `hace ${min} min`
  const horas = Math.round(min / 60)
  if (horas < 24) return `hace ${horas} h`
  const dias = Math.round(horas / 24)
  return `hace ${dias} d`
}

// Animación de conteo — sin librerías, `requestAnimationFrame` con
// easing simple. Se guarda el valor mostrado por clave en `contadores`
// (reactivo) para que el template solo lea números ya animados.
const contadores = ref({})
function animarContador(clave, valorFinal, duracionMs = 900) {
  if (valorFinal == null) return
  const inicio = performance.now()
  function paso(ahora) {
    const t = Math.min(1, (ahora - inicio) / duracionMs)
    const facil = 1 - (1 - t) * (1 - t)
    contadores.value = { ...contadores.value, [clave]: Math.round(valorFinal * facil) }
    if (t < 1) requestAnimationFrame(paso)
  }
  requestAnimationFrame(paso)
}

async function cargarTecnicos() {
  if (!auth.tienePermiso('usuarios.gestionar')) return
  try {
    const { data } = await api.get('/usuarios')
    stats.value.tecnicos = data.length
    stats.value.activos = data.filter((u) => u.estado === 'ACTIVO').length
    tecnicosPorId.value = new Map(data.map((u) => [u.id, u]))
    animarContador('tecnicos', stats.value.tecnicos)
    animarContador('activos', stats.value.activos)
  } catch {
    // silencioso — la tarjeta simplemente no se muestra sin dato
  }
}

async function cargarEcas() {
  if (!auth.tienePermiso('ecas.ver')) return
  try {
    const { total } = await listarEcas({ pageSize: 1 })
    stats.value.ecas = total
    animarContador('ecas', total)
  } catch {
    // silencioso
  }
}

async function cargarActividades() {
  if (!auth.tienePermiso('actividades.ver_todas')) return
  try {
    const { total, resultados } = await listarActividades({ page: 1, pageSize: 5 })
    stats.value.actividades = total
    actividadesRecientes.value = resultados
    animarContador('actividades', total)
  } catch {
    // silencioso
  }
}

onMounted(async () => {
  await Promise.all([cargarTecnicos(), cargarEcas(), cargarActividades()])
  cargando.value = false
})
</script>

<template>
  <section class="dash">
    <!-- Hero: saludo + fecha + avatar, con el mismo fondo verde degradado
         del resto del panel pero con "blobs" animados de admin-pwa/Sidebar
         para el acabado premium. -->
    <div class="dash-hero eca-entrar">
      <span class="dash-hero__blob dash-hero__blob--a" aria-hidden="true"></span>
      <span class="dash-hero__blob dash-hero__blob--b" aria-hidden="true"></span>
      <div class="dash-hero__texto">
        <p class="dash-hero__fecha">{{ fechaHoy }}</p>
        <h1 class="dash-hero__saludo">
          {{ saludo }}, {{ auth.usuario?.nombre || 'Administrador' }}
          <AuthIcon name="sparkles" class="dash-hero__chispa" />
        </h1>
        <p class="dash-hero__sub">Este es el resumen de Escuelas de Campo hoy.</p>
      </div>
      <div class="dash-hero__avatar">
        <span>{{ iniciales() }}</span>
        <span v-if="rolPrincipal()" class="dash-hero__rol">{{ rolPrincipal() }}</span>
      </div>
    </div>

    <!-- Estadísticas — cada tarjeta solo aparece si hubo permiso/dato. -->
    <div class="dash-stats">
      <RouterLink
        v-if="stats.tecnicos !== null"
        :to="{ name: 'tecnicos' }"
        class="dash-stat dash-stat--morado eca-entrar"
        style="--eca-delay: 0.05s"
      >
        <span class="dash-stat__icono"><AuthIcon name="user" /></span>
        <span class="dash-stat__valor">{{ contadores.tecnicos ?? 0 }}</span>
        <span class="dash-stat__etiqueta">Técnicos registrados</span>
        <span class="dash-stat__pie"><AuthIcon name="check-circle" /> {{ contadores.activos ?? 0 }} activos</span>
      </RouterLink>

      <RouterLink
        v-if="stats.actividades !== null"
        :to="{ name: 'actividades' }"
        class="dash-stat dash-stat--verde eca-entrar"
        style="--eca-delay: 0.1s"
      >
        <span class="dash-stat__icono"><AuthIcon name="activity" /></span>
        <span class="dash-stat__valor">{{ contadores.actividades ?? 0 }}</span>
        <span class="dash-stat__etiqueta">Actividades registradas</span>
        <span class="dash-stat__pie"><AuthIcon name="trending-up" /> en toda la app</span>
      </RouterLink>

      <RouterLink
        v-if="stats.ecas !== null"
        :to="{ name: 'ecas' }"
        class="dash-stat dash-stat--azul eca-entrar"
        style="--eca-delay: 0.15s"
      >
        <span class="dash-stat__icono"><AuthIcon name="school" /></span>
        <span class="dash-stat__valor">{{ contadores.ecas ?? 0 }}</span>
        <span class="dash-stat__etiqueta">Escuelas de Campo</span>
        <span class="dash-stat__pie"><AuthIcon name="map-pin" /> en el país</span>
      </RouterLink>

    </div>

    <div class="dash-columnas">
      <!-- Accesos rápidos -->
      <div class="dash-panel eca-entrar" style="--eca-delay: 0.25s">
        <h2 class="dash-panel__titulo"><AuthIcon name="sparkles" /> Accesos rápidos</h2>
        <div class="dash-accesos">
          <RouterLink
            v-for="(enlace, i) in enlacesVisibles"
            :key="enlace.nombre"
            :to="{ name: enlace.nombre }"
            class="dash-acceso"
            :class="`dash-acceso--${enlace.color}`"
            :style="{ '--eca-delay': `${0.28 + i * 0.04}s` }"
          >
            <span class="dash-acceso__icono"><AuthIcon :name="enlace.icono" /></span>
            <span>{{ enlace.etiqueta }}</span>
          </RouterLink>
        </div>
      </div>

      <!-- Actividad reciente -->
      <div v-if="auth.tienePermiso('actividades.ver_todas')" class="dash-panel eca-entrar" style="--eca-delay: 0.3s">
        <h2 class="dash-panel__titulo"><AuthIcon name="clock" /> Actividad reciente</h2>
        <p v-if="cargando" class="eca-ayuda">Cargando…</p>
        <div v-else-if="!actividadesRecientes.length" class="eca-vacio dash-vacio">
          <AuthIcon name="inbox" />
          <p>Todavía no hay actividades registradas.</p>
        </div>
        <ul v-else class="dash-feed">
          <li v-for="a in actividadesRecientes" :key="a.uuid">
            <span class="eca-avatar dash-feed__avatar">{{ iniciales_de(tecnicosPorId.get(a.usuario_id)) }}</span>
            <span class="dash-feed__texto">
              <strong>{{ tecnicosPorId.get(a.usuario_id)?.nombre || `Técnico #${a.usuario_id}` }}</strong>
              <span>{{ a.descripcion }}</span>
            </span>
            <span class="dash-feed__tiempo">{{ tiempoRelativo(a.fecha_hora) }}</span>
          </li>
        </ul>
        <RouterLink :to="{ name: 'actividades' }" class="dash-panel__vertodo">
          Ver todas <AuthIcon name="arrow-right" />
        </RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ---- Entrada escalonada, mismo criterio que pwa-eca (`.eca-entrar`),
   introducido aquí porque admin-eca no tenía ninguna animación de
   entrada todavía. ---- */
.eca-entrar {
  animation: dash-aparecer 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--eca-delay, 0s);
}
@keyframes dash-aparecer {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ---- Hero ---- */
.dash-hero {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.75rem 2rem;
  border-radius: 28px;
  background: linear-gradient(135deg, #4caf50 0%, #2e7d32 60%, #1b5e20 100%);
  border: 2px solid #8bc34a;
  box-shadow: 0 16px 40px rgba(27, 94, 32, 0.28);
  color: #fff;
}
.dash-hero__blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(30px);
  pointer-events: none;
}
.dash-hero__blob--a {
  width: 220px;
  height: 220px;
  top: -80px;
  right: 8%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.28) 0%, transparent 70%);
  animation: dash-flotar-a 9s ease-in-out infinite;
}
.dash-hero__blob--b {
  width: 180px;
  height: 180px;
  bottom: -70px;
  left: 20%;
  background: radial-gradient(circle, rgba(139, 195, 74, 0.35) 0%, transparent 70%);
  animation: dash-flotar-b 11s ease-in-out infinite;
}
@keyframes dash-flotar-a {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-16px, 14px) scale(1.12); }
}
@keyframes dash-flotar-b {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(14px, -10px) scale(1.08); }
}
.dash-hero__texto {
  position: relative;
  z-index: 1;
  min-width: 0;
}
.dash-hero__fecha {
  margin: 0 0 0.3rem;
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: capitalize;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 0.02em;
}
.dash-hero__saludo {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  letter-spacing: -0.01em;
}
.dash-hero__chispa {
  width: 1.1rem;
  height: 1.1rem;
  color: #ffe066;
  animation: dash-brillo 2.4s ease-in-out infinite;
}
@keyframes dash-brillo {
  0%, 100% { opacity: 0.6; transform: scale(1) rotate(0deg); }
  50% { opacity: 1; transform: scale(1.2) rotate(15deg); }
}
.dash-hero__sub {
  margin: 0.4rem 0 0;
  font-size: 0.92rem;
  color: rgba(255, 255, 255, 0.88);
}
.dash-hero__avatar {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  width: 4.2rem;
  height: 4.2rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  border: 2px solid rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: 800;
  backdrop-filter: blur(6px);
}
.dash-hero__rol {
  position: absolute;
  bottom: -0.6rem;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  background: #fff;
  color: var(--eca-green-700);
  font-size: 0.62rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* ---- Stats ---- */
.dash-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 1rem;
}
.dash-stat {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 1.25rem 1.3rem;
  border-radius: var(--eca-r-lg);
  background: #fff;
  border: 1px solid var(--eca-surface-border);
  box-shadow: var(--eca-shadow-card);
  text-decoration: none;
  color: inherit;
  overflow: hidden;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.25s ease;
}
.dash-stat::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.06;
  background: var(--dash-grad);
}
.dash-stat:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 32px rgba(20, 20, 30, 0.14);
}
.dash-stat--morado { --dash-grad: linear-gradient(135deg, var(--eca-purple-600), var(--eca-purple-500)); }
.dash-stat--verde { --dash-grad: linear-gradient(135deg, #34d399, var(--eca-green-600)); }
.dash-stat--azul { --dash-grad: linear-gradient(135deg, #38bdf8, #0284c7); }
.dash-stat--ambar { --dash-grad: linear-gradient(135deg, #fbbf24, #d97706); }
.dash-stat__icono {
  position: relative;
  z-index: 1;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: var(--eca-r-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: var(--dash-grad);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
}
.dash-stat__icono svg { width: 1.2rem; height: 1.2rem; }
.dash-stat__valor {
  position: relative;
  z-index: 1;
  font-size: 1.9rem;
  font-weight: 800;
  color: var(--eca-ink);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.dash-stat__etiqueta {
  position: relative;
  z-index: 1;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--eca-ink-soft);
}
.dash-stat__pie {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.15rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--eca-ink-faint, #9aa1af);
}
.dash-stat__pie svg { width: 12px; height: 12px; }

/* ---- Columnas inferiores ---- */
.dash-columnas {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  align-items: start;
}
@media (max-width: 900px) {
  .dash-columnas {
    grid-template-columns: 1fr;
  }
  .dash-hero {
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }
}

.dash-panel {
  background: #fff;
  border-radius: var(--eca-r-lg);
  border: 1px solid var(--eca-surface-border);
  box-shadow: var(--eca-shadow-card);
  padding: 1.25rem 1.4rem;
}
.dash-panel__titulo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-size: 1rem;
  color: var(--eca-ink);
}
.dash-panel__titulo svg {
  width: 1.05rem;
  height: 1.05rem;
  color: var(--eca-green-600);
}

/* Accesos rápidos */
.dash-accesos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 0.7rem;
}
.dash-acceso {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 0.5rem;
  border-radius: var(--eca-r-md);
  background: var(--eca-surface);
  text-decoration: none;
  color: var(--eca-ink);
  font-size: 0.78rem;
  font-weight: 700;
  text-align: center;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.2s ease, box-shadow 0.2s ease;
}
.dash-acceso:hover {
  transform: translateY(-3px) scale(1.03);
  box-shadow: 0 10px 22px rgba(20, 20, 30, 0.12);
}
.dash-acceso__icono {
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.dash-acceso__icono svg { width: 1.1rem; height: 1.1rem; }
.dash-acceso--morado .dash-acceso__icono { background: linear-gradient(135deg, var(--eca-purple-600), var(--eca-purple-500)); }
.dash-acceso--verde .dash-acceso__icono { background: linear-gradient(135deg, #34d399, var(--eca-green-600)); }
.dash-acceso--azul .dash-acceso__icono { background: linear-gradient(135deg, #38bdf8, #0284c7); }
.dash-acceso--ambar .dash-acceso__icono { background: linear-gradient(135deg, #fbbf24, #d97706); }

/* Actividad reciente */
.dash-vacio {
  padding: 2rem 1rem;
}
.dash-feed {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.dash-feed li {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem;
  border-radius: var(--eca-r-md);
  transition: background 0.15s ease;
}
.dash-feed li:hover {
  background: var(--eca-surface);
}
.dash-feed__avatar {
  width: 2rem;
  height: 2rem;
  font-size: 0.68rem;
  flex-shrink: 0;
}
.dash-feed__texto {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.dash-feed__texto strong {
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dash-feed__texto span {
  font-size: 0.76rem;
  color: var(--eca-ink-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dash-feed__tiempo {
  flex-shrink: 0;
  font-size: 0.7rem;
  color: var(--eca-ink-faint, #9aa1af);
  font-weight: 600;
}
.dash-panel__vertodo {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-top: 0.9rem;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--eca-green-700);
  text-decoration: none;
}
.dash-panel__vertodo svg { width: 13px; height: 13px; }
.dash-panel__vertodo:hover { text-decoration: underline; }

@media (max-width: 480px) {
  .dash-hero {
    padding: 1.4rem 1.3rem;
  }
  .dash-hero__saludo {
    font-size: 1.25rem;
  }
}
</style>
