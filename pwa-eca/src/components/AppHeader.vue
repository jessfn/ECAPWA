<!-- pwa-eca — barra superior + menú hamburguesa de la app autenticada.
     Paridad de diseño pedida explícitamente con `pwasuper`: header verde
     fijo con zona segura (notch/isla dinámica), indicador en línea/sin
     conexión, y menú desplegable con toda la navegación real de esta app
     (antes solo `InicioView` tenía un header improvisado; el resto de
     pantallas no tenía ninguna forma de navegar entre sí). -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useConectividad } from '../services/conectividad'
import AuthIcon from './auth/AuthIcon.vue'

const route = useRoute()
const auth = useAuthStore()
const { enLinea } = useConectividad()

const menuAbierto = ref(false)

// Hora y fecha de Ciudad de México — pedido explícito: "sin editarse del
// dispositivo", o sea que no dependa del reloj del celular (un técnico
// puede traerlo mal puesto). Se obtiene la hora real de un servicio de
// internet una vez, se calcula el desfase contra el reloj del propio
// dispositivo, y de ahí en adelante se corrige ese desfase cada segundo
// (sin volver a pedirla constantemente) — con resincronización periódica
// por si acaso. Si no hay red, se usa el reloj del dispositivo como
// respaldo (mejor esfuerzo, nunca bloquea — mismo espíritu que el GPS).
const horaActual = ref('')
const fechaActual = ref('')
let intervaloReloj = null
let intervaloResincronizar = null
let desfaseMs = 0
// Si nunca se logra sincronizar (sin red, o el servicio no responde), se
// cae de vuelta al reloj del dispositivo — pero convertido de verdad al
// huso de CDMX (no la falsa base UTC de abajo), para que al menos la
// zona horaria salga bien aunque la hora exacta dependa del celular.
let sincronizado = false

async function sincronizarConInternet() {
  try {
    // timeapi.io ya entrega los campos de la hora de pared de CDMX
    // directamente (año/mes/día/hora/minuto/segundo), sin que este código
    // tenga que calcular el desfase UTC de México (que además cambia con
    // el horario de verano) — se arma una fecha "UTC falsa" con esos
    // mismos números y se ancla contra el reloj del dispositivo una sola
    // vez; de ahí en adelante solo se le suma el tiempo transcurrido.
    const respuesta = await fetch('https://timeapi.io/api/Time/current/zone?timeZone=America/Mexico_City', {
      cache: 'no-store',
    })
    if (!respuesta.ok) return
    const d = await respuesta.json()
    const baseFalsoUtc = Date.UTC(d.year, d.month - 1, d.day, d.hour, d.minute, d.seconds)
    desfaseMs = baseFalsoUtc - Date.now()
    sincronizado = true
  } catch {
    sincronizado = false
    // Sin red: se sigue mostrando la hora del dispositivo (con el huso de
    // CDMX ya aplicado), nunca se bloquea la barra por esto.
  }
}

function actualizarReloj() {
  const ahora = sincronizado ? new Date(Date.now() + desfaseMs) : new Date()
  const huso = sincronizado ? 'UTC' : 'America/Mexico_City'
  horaActual.value = new Intl.DateTimeFormat('es-MX', {
    timeZone: huso,
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(ahora)
  fechaActual.value = new Intl.DateTimeFormat('es-MX', {
    timeZone: huso,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(ahora)
}

const enlaces = [
  { nombre: 'inicio', etiqueta: 'Inicio', icono: 'home' },
  { nombre: 'jornada', etiqueta: 'Jornada', icono: 'calendar' },
  { nombre: 'nueva-actividad', etiqueta: 'Nueva actividad', icono: 'plus-circle' },
  { nombre: 'sincronizacion', etiqueta: 'Sincronización', icono: 'sync' },
  { nombre: 'historial', etiqueta: 'Historial', icono: 'clock' },
  { nombre: 'perfil', etiqueta: 'Mi perfil', icono: 'user' },
]

function alternarMenu() {
  menuAbierto.value = !menuAbierto.value
}

function cerrarMenu() {
  menuAbierto.value = false
}

async function cerrarSesion() {
  cerrarMenu()
  await auth.logout()
  // Bug real encontrado: `router.push({ name: 'login' })` (navegación de
  // Vue Router dentro de la SPA) se quedaba pegado en la pantalla actual
  // — el store SÍ quedaba sin sesión (tokens y sesión local borrados),
  // pero la vista no cambiaba y el usuario seguía viendo el contenido
  // protegido. Confirmado que una recarga completa de la página sí
  // redirige bien a `/login` (el guard de rutas funciona correctamente
  // en la carga inicial). Se fuerza entonces una navegación completa del
  // navegador en vez de depender del router de la SPA — así funciona sin
  // importar la causa exacta de esa navegación pegada, y de paso deja el
  // estado de la app completamente limpio para la siguiente sesión.
  window.location.href = '/login'
}

onMounted(async () => {
  await sincronizarConInternet()
  actualizarReloj()
  intervaloReloj = setInterval(actualizarReloj, 1000)
  // Resincroniza cada 5 minutos: corrige cualquier deriva del reloj del
  // dispositivo en sesiones largas, sin pedir la hora a internet a cada
  // segundo.
  intervaloResincronizar = setInterval(sincronizarConInternet, 5 * 60 * 1000)
})
onUnmounted(() => {
  if (intervaloReloj) clearInterval(intervaloReloj)
  if (intervaloResincronizar) clearInterval(intervaloResincronizar)
})
</script>

<template>
  <header class="app-header" :class="{ 'app-header--abierto': menuAbierto }">
    <div class="app-header__fila">
      <div class="app-header__marca">
        <span class="app-header__logo">
          <AuthIcon name="leaf" />
        </span>
        <span class="app-header__marca-texto">
          <span class="app-header__nombre">ECA</span>
          <span class="app-header__usuario">Aplicación de seguimiento</span>
        </span>
      </div>

      <div class="app-header__acciones">
        <button
          type="button"
          class="app-header__hamburguesa"
          :aria-expanded="menuAbierto"
          aria-label="Abrir menú"
          @click="alternarMenu"
        >
          <AuthIcon :name="menuAbierto ? 'close' : 'menu'" />
        </button>
      </div>
    </div>

    <div class="app-header__estado">
      <span class="app-header__estado-pill" :class="{ 'app-header__estado-pill--offline': !enLinea }" role="status">
        <AuthIcon :name="enLinea ? 'wifi' : 'wifi-off'" />
        <span>{{ enLinea ? 'En línea' : 'Sin conexión' }}</span>
      </span>
      <span class="app-header__reloj">
        <span class="app-header__hora">{{ horaActual }}</span>
        <span class="app-header__fecha">{{ fechaActual }}</span>
      </span>
    </div>
  </header>

  <Transition name="menu-slide">
    <nav v-if="menuAbierto" class="app-menu">
      <RouterLink
        v-for="enlace in enlaces"
        :key="enlace.nombre"
        :to="{ name: enlace.nombre }"
        class="app-menu__enlace"
        :class="{ 'app-menu__enlace--activo': route.name === enlace.nombre }"
        @click="cerrarMenu"
      >
        <AuthIcon :name="enlace.icono" />
        <span>{{ enlace.etiqueta }}</span>
      </RouterLink>

      <div class="app-menu__separador"></div>

      <button type="button" class="app-menu__enlace app-menu__salir" @click="cerrarSesion">
        <AuthIcon name="logout" />
        <span>Cerrar sesión</span>
      </button>
    </nav>
  </Transition>

  <div v-if="menuAbierto" class="app-menu__overlay" @click="cerrarMenu"></div>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: max(8px, calc(env(safe-area-inset-top, 0px) + 8px));
  left: 8px;
  right: 8px;
  z-index: 40;
  /* Fila y barra de estado deben verse como una sola pieza, sin ninguna
     costura entre ellas — a prueba de fallos: en vez de depender solo del
     recorte de `overflow: hidden` (que en algunos navegadores móviles no
     siempre recorta bien un `border-radius` sobre `position: fixed`), la
     franja de estado también lleva el MISMO fondo explícito abajo, así
     que aunque el recorte fallara no se vería ninguna línea. */
  display: flex;
  flex-direction: column;
  background: var(--eca-green-900);
  color: #fff;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: var(--eca-shadow-card);
  transition: border-radius 0.2s ease;
}
.app-header--abierto {
  border-radius: 24px 24px 0 0;
}
.app-header--abierto .app-header__estado {
  border-radius: 0;
}
.app-header__fila {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.6rem 0.9rem;
  margin: 0;
  flex-shrink: 0;
}
.app-header__marca {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}
.app-header__logo {
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--eca-green-900);
  border: 1.5px solid rgba(255, 255, 255, 0.65);
  color: var(--eca-green-200);
}
.app-header__logo svg {
  width: 1.05rem;
  height: 1.05rem;
}
.app-header__marca-texto {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.app-header__nombre {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--eca-green-200);
  text-transform: uppercase;
}
.app-header__usuario {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.75);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 46vw;
}
.app-header__acciones {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}
/* Fila de estado: pegada justo debajo de la barra superior (mismo
   contenedor, `overflow: hidden` del padre le da las esquinas redondeadas
   solo abajo). Adentro: una píldora compacta de conexión (verde manzana
   fuerte, angosta — no toda la fila) a la izquierda, y la hora local del
   técnico a la derecha — pedido explícito. */
.app-header__estado {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  padding: 0.45rem 0.9rem 0.55rem;
  margin: 0;
  background: var(--eca-green-900);
  border-radius: 0 0 24px 24px;
  flex-shrink: 0;
}
.app-header__estado-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  background: #4ade80;
  color: #052e16;
  flex-shrink: 0;
}
.app-header__estado-pill svg {
  width: 11px;
  height: 11px;
}
.app-header__estado-pill--offline {
  background: #fbbf24;
  color: #451a03;
}
.app-header__reloj {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  line-height: 1.2;
}
.app-header__hora {
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.app-header__fecha {
  font-size: 0.62rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.55);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.app-header__hamburguesa {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  cursor: pointer;
  transition: background 0.15s ease;
}
.app-header__hamburguesa:hover {
  background: rgba(255, 255, 255, 0.22);
}
.app-header__hamburguesa svg {
  width: 20px;
  height: 20px;
}

.app-menu {
  position: fixed;
  top: calc(90px + env(safe-area-inset-top, 0px));
  left: 8px;
  right: 8px;
  z-index: 30;
  background: var(--eca-green-900);
  border-radius: 0 0 24px 24px;
  box-shadow: var(--eca-shadow-card);
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.app-menu__enlace {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.65rem 0.75rem;
  border-radius: 12px;
  color: #fff;
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 500;
  border: none;
  background: transparent;
  cursor: pointer;
  width: 100%;
  text-align: left;
}
.app-menu__enlace svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
.app-menu__enlace:hover {
  background: rgba(255, 255, 255, 0.1);
}
.app-menu__enlace--activo {
  background: var(--eca-green-600);
}
.app-menu__separador {
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  margin: 0.3rem 0;
}
.app-menu__salir {
  color: #fecaca;
}
.app-menu__salir:hover {
  background: rgba(220, 38, 38, 0.18);
}

.app-menu__overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  z-index: 20;
}

.menu-slide-enter-active,
.menu-slide-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.menu-slide-enter-from,
.menu-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
