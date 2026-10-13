<!-- pwa-eca — centro de notificaciones del técnico. Hoja inferior en celular y
     popover bajo la barra en pantallas grandes. Lista agrupada por día (hora de
     CDMX) con tarjetas de color por tipo, punto de "sin leer", miniatura, y
     vista de detalle con galería de imágenes, reproductor de video y botón de
     acción. Todo con transiciones tipo resorte y respetando la zona segura. -->
<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificacionesStore } from '../stores/notificaciones'
import AuthIcon from './auth/AuthIcon.vue'
import { estadoPush, activarPush } from '../services/push'

const store = useNotificacionesStore()
const router = useRouter()
const API = import.meta.env.VITE_API_URL || ''
const ZONA = 'America/Mexico_City'

const COLORES = { INFO: '#2563eb', EXITO: '#16a34a', ALERTA: '#d97706', URGENTE: '#dc2626' }
const ETIQUETAS = { INFO: 'Aviso', EXITO: 'Éxito', ALERTA: 'Alerta', URGENTE: 'Urgente' }

const pestana = ref('todas')
const visibles = computed(() => (pestana.value === 'sin_leer' ? store.items.filter((n) => !n.leida) : store.items))

// --- agrupar por día en CDMX
const claveDia = (d) => new Intl.DateTimeFormat('en-CA', { timeZone: ZONA }).format(d)
const grupos = computed(() => {
  const hoy = claveDia(new Date())
  const ayer = claveDia(new Date(Date.now() - 86400000))
  const mapa = new Map()
  for (const n of visibles.value) {
    const dia = claveDia(new Date(n.publicada_en))
    const etiqueta =
      dia === hoy
        ? 'Hoy'
        : dia === ayer
          ? 'Ayer'
          : new Intl.DateTimeFormat('es-MX', { timeZone: ZONA, day: 'numeric', month: 'long' }).format(new Date(n.publicada_en))
    if (!mapa.has(etiqueta)) mapa.set(etiqueta, [])
    mapa.get(etiqueta).push(n)
  }
  return [...mapa].map(([etiqueta, lista]) => ({ etiqueta, lista }))
})

function hace(iso) {
  const seg = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (seg < 60) return 'Ahora'
  if (seg < 3600) return `hace ${Math.floor(seg / 60)} min`
  if (seg < 86400) return `hace ${Math.floor(seg / 3600)} h`
  return new Intl.DateTimeFormat('es-MX', { timeZone: ZONA, hour: 'numeric', minute: '2-digit', hour12: true }).format(new Date(iso))
}
function fechaCompleta(iso) {
  return new Intl.DateTimeFormat('es-MX', {
    timeZone: ZONA, weekday: 'long', day: 'numeric', month: 'long', hour: 'numeric', minute: '2-digit', hour12: true,
  }).format(new Date(iso))
}
const medio = (a) => `${API}${a.url}`
const primeraImagen = (n) => n.adjuntos.find((a) => a.tipo === 'IMAGEN')
const hayVideo = (n) => n.adjuntos.some((a) => a.tipo === 'VIDEO')

// --- avisos push (invitación a activarlos en este dispositivo)
const estadoDelPush = ref('activo')
const activando = ref(false)
const errorPush = ref('')
async function refrescarEstadoPush() {
  estadoDelPush.value = await estadoPush()
}
async function activar() {
  activando.value = true
  errorPush.value = ''
  try {
    await activarPush()
  } catch (e) {
    errorPush.value = e?.message || 'No se pudieron activar los avisos.'
  } finally {
    activando.value = false
    await refrescarEstadoPush()
  }
}

// --- detalle y visor de imágenes
const detalle = computed(() => store.detalle)
const imagenAmpliada = ref(null)

function abrir(n) {
  store.detalleUuid = n.uuid
  store.marcarLeida(n.uuid)
}
function volver() {
  store.detalleUuid = null
}
function accion(n) {
  const url = n.url
  if (!url) return
  if (url.startsWith('/')) {
    store.cerrarPanel()
    router.push(url)
  } else {
    window.open(url, '_blank', 'noopener')
  }
}

// Si cambia la lista y el detalle abierto ya no existe (retirada), se regresa.
watch(
  () => store.items,
  () => {
    if (store.detalleUuid && !store.detalle) store.detalleUuid = null
  },
)

// Bloquea el scroll del fondo mientras el panel está abierto.
watch(
  () => store.panelAbierto,
  (abierto) => {
    document.body.style.overflow = abierto ? 'hidden' : ''
    if (abierto) {
      pestana.value = 'todas'
      store.cargar()
      refrescarEstadoPush()
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="np-fondo">
      <div v-if="store.panelAbierto" class="np-fondo" @click.self="store.cerrarPanel()">
        <Transition name="np-hoja" appear>
          <section class="np" role="dialog" aria-modal="true" aria-label="Notificaciones">
            <div class="np__asa" aria-hidden="true"></div>

            <!-- ============ Lista ============ -->
            <template v-if="!detalle">
              <header class="np__cab">
                <div class="np__cab-texto">
                  <h2>Notificaciones</h2>
                  <p>{{ store.noLeidas ? `${store.noLeidas} sin leer` : 'Estás al día' }}</p>
                </div>
                <button
                  v-if="store.noLeidas"
                  type="button"
                  class="np__icono-btn"
                  title="Marcar todas como leídas"
                  aria-label="Marcar todas como leídas"
                  @click="store.marcarTodasLeidas()"
                >
                  <AuthIcon name="check-all" />
                </button>
                <button type="button" class="np__icono-btn" aria-label="Cerrar" @click="store.cerrarPanel()">
                  <AuthIcon name="close" />
                </button>
              </header>

              <div class="np__pestanas" role="tablist">
                <button type="button" role="tab" :class="{ 'np__pestana--activa': pestana === 'todas' }" @click="pestana = 'todas'">Todas</button>
                <button type="button" role="tab" :class="{ 'np__pestana--activa': pestana === 'sin_leer' }" @click="pestana = 'sin_leer'">
                  Sin leer<span v-if="store.noLeidas" class="np__contador">{{ store.noLeidas }}</span>
                </button>
              </div>

              <p v-if="store.sinConexion" class="np__aviso-offline">Sin conexión · mostrando lo último guardado</p>

              <div v-if="['inactivo', 'requiere_instalar', 'bloqueado'].includes(estadoDelPush)" class="np-push">
                <span class="np-push__icono"><AuthIcon name="bell" /></span>
                <div class="np-push__texto">
                  <template v-if="estadoDelPush === 'inactivo'">
                    <strong>Recibe los avisos con la app cerrada</strong>
                    <small>Actívalos en este dispositivo.</small>
                  </template>
                  <template v-else-if="estadoDelPush === 'requiere_instalar'">
                    <strong>Instala la app para recibir avisos</strong>
                    <small>Toca Compartir y elige «Añadir a pantalla de inicio»; luego ábrela desde ahí.</small>
                  </template>
                  <template v-else>
                    <strong>Avisos bloqueados</strong>
                    <small>Actívalos en los ajustes del navegador para este sitio.</small>
                  </template>
                  <small v-if="errorPush" class="np-push__error">{{ errorPush }}</small>
                </div>
                <button v-if="estadoDelPush === 'inactivo'" type="button" :disabled="activando" @click="activar">
                  {{ activando ? '…' : 'Activar' }}
                </button>
              </div>

              <div class="np__lista">
                <!-- Esqueleto de carga -->
                <template v-if="!store.cargado && !store.items.length">
                  <div v-for="i in 4" :key="i" class="np-esqueleto">
                    <span class="np-esqueleto__circulo"></span>
                    <span class="np-esqueleto__lineas"><i></i><i></i></span>
                  </div>
                </template>

                <div v-else-if="!visibles.length" class="np__vacio">
                  <span class="np__vacio-icono"><AuthIcon name="inbox" /></span>
                  <strong>{{ pestana === 'sin_leer' ? 'Todo leído' : 'Sin notificaciones' }}</strong>
                  <p>{{ pestana === 'sin_leer' ? 'No tienes avisos pendientes.' : 'Cuando haya un aviso nuevo aparecerá aquí.' }}</p>
                </div>

                <TransitionGroup v-else name="np-fila" tag="div" class="np__grupos">
                  <section v-for="g in grupos" :key="g.etiqueta" class="np__grupo">
                    <h3>{{ g.etiqueta }}</h3>
                    <button
                      v-for="n in g.lista"
                      :key="n.uuid"
                      type="button"
                      class="np-tarjeta"
                      :class="{ 'np-tarjeta--nueva': !n.leida }"
                      :style="{ '--c': COLORES[n.tipo] }"
                      @click="abrir(n)"
                    >
                      <span class="np-tarjeta__icono"><AuthIcon name="bell" /></span>
                      <span class="np-tarjeta__texto">
                        <span class="np-tarjeta__meta">
                          <b>{{ ETIQUETAS[n.tipo] }}</b>
                          <time>{{ hace(n.publicada_en) }}</time>
                        </span>
                        <strong>{{ n.titulo }}</strong>
                        <em v-if="n.subtitulo">{{ n.subtitulo }}</em>
                        <span v-if="n.descripcion" class="np-tarjeta__desc">{{ n.descripcion }}</span>
                        <span v-if="hayVideo(n) && !primeraImagen(n)" class="np-tarjeta__chip"><AuthIcon name="play" /> Video</span>
                      </span>
                      <span v-if="primeraImagen(n)" class="np-tarjeta__miniatura">
                        <img :src="medio(primeraImagen(n))" alt="" loading="lazy" />
                      </span>
                      <i v-if="!n.leida" class="np-tarjeta__punto" aria-label="Sin leer"></i>
                    </button>
                  </section>
                </TransitionGroup>
              </div>
            </template>

            <!-- ============ Detalle ============ -->
            <template v-else>
              <header class="np__cab np__cab--detalle">
                <button type="button" class="np__icono-btn" aria-label="Volver" @click="volver">
                  <AuthIcon name="arrow-left" />
                </button>
                <div class="np__cab-texto">
                  <h2 :style="{ color: COLORES[detalle.tipo] }" class="np__tipo">{{ ETIQUETAS[detalle.tipo] }}</h2>
                  <p>{{ fechaCompleta(detalle.publicada_en) }}</p>
                </div>
                <button type="button" class="np__icono-btn" aria-label="Cerrar" @click="store.cerrarPanel()">
                  <AuthIcon name="close" />
                </button>
              </header>

              <article class="np-detalle" :style="{ '--c': COLORES[detalle.tipo] }">
                <h1>{{ detalle.titulo }}</h1>
                <p v-if="detalle.subtitulo" class="np-detalle__sub">{{ detalle.subtitulo }}</p>

                <div v-if="detalle.adjuntos.length" class="np-detalle__media" :class="{ 'np-detalle__media--uno': detalle.adjuntos.length === 1 }">
                  <template v-for="a in detalle.adjuntos" :key="a.uuid">
                    <video v-if="a.tipo === 'VIDEO'" :src="medio(a)" controls playsinline preload="metadata"></video>
                    <button v-else type="button" class="np-detalle__img" @click="imagenAmpliada = a">
                      <img :src="medio(a)" alt="" loading="lazy" />
                    </button>
                  </template>
                </div>

                <p v-if="detalle.descripcion" class="np-detalle__desc">{{ detalle.descripcion }}</p>

                <button v-if="detalle.url" type="button" class="np-detalle__boton" @click="accion(detalle)">
                  <AuthIcon name="link" /> {{ detalle.url_texto || 'Abrir enlace' }}
                </button>
              </article>
            </template>
          </section>
        </Transition>
      </div>
    </Transition>

    <!-- Visor de imagen a pantalla completa -->
    <Transition name="np-fondo">
      <div v-if="imagenAmpliada" class="np-visor" @click="imagenAmpliada = null">
        <button type="button" class="np-visor__cerrar" aria-label="Cerrar imagen"><AuthIcon name="close" /></button>
        <img :src="medio(imagenAmpliada)" alt="" />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.np-fondo {
  position: fixed; inset: 0; z-index: 60;
  background: rgba(2, 20, 10, 0.5); backdrop-filter: blur(6px);
  display: flex; align-items: flex-end; justify-content: center;
}
.np-fondo-enter-active, .np-fondo-leave-active { transition: opacity 0.25s ease; }
.np-fondo-enter-from, .np-fondo-leave-to { opacity: 0; }

.np {
  position: relative; width: 100%; max-width: 520px; height: 88dvh; max-height: 88dvh;
  display: flex; flex-direction: column;
  background: linear-gradient(180deg, #ffffff 0%, #f4faf6 100%);
  border-radius: 28px 28px 0 0;
  box-shadow: 0 -20px 60px rgba(2, 20, 10, 0.35);
  padding-bottom: env(safe-area-inset-bottom, 0px);
  overflow: hidden;
}
.np-hoja-enter-active { transition: transform 0.45s cubic-bezier(0.32, 1.2, 0.5, 1), opacity 0.25s ease; }
.np-hoja-leave-active { transition: transform 0.22s ease, opacity 0.2s ease; }
.np-hoja-enter-from, .np-hoja-leave-to { transform: translateY(40px) scale(0.98); opacity: 0; }

/* Escritorio: popover anclado bajo la barra */
@media (min-width: 720px) {
  .np-fondo { align-items: flex-start; justify-content: flex-end; background: rgba(2, 20, 10, 0.18); backdrop-filter: none; }
  .np {
    margin: calc(max(8px, env(safe-area-inset-top, 0px) + 8px) + 100px) 12px 0 0;
    height: auto; max-height: min(640px, calc(100dvh - 130px)); min-height: 360px;
    border-radius: 24px; width: 420px;
  }
  .np__asa { display: none; }
}

.np__asa { width: 2.6rem; height: 0.28rem; border-radius: 99px; background: #cfe0d5; margin: 0.55rem auto 0; flex-shrink: 0; }

.np__cab { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem 0.5rem; flex-shrink: 0; }
.np__cab-texto { flex: 1; min-width: 0; }
.np__cab h2 { margin: 0; font-size: 1.3rem; font-weight: 800; color: var(--eca-ink); letter-spacing: -0.01em; }
.np__cab p { margin: 0.1rem 0 0; font-size: 0.78rem; color: var(--eca-ink-soft); }
.np__cab--detalle p::first-letter { text-transform: uppercase; }
.np__cab--detalle h2 { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; }
.np__icono-btn {
  width: 2.3rem; height: 2.3rem; flex-shrink: 0; border: none; border-radius: 50%;
  background: #e8f3ec; color: var(--eca-green-700); display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.15s;
}
.np__icono-btn:hover { background: #d6ecdc; transform: scale(1.08); }
.np__icono-btn:active { transform: scale(0.92); }
.np__icono-btn svg { width: 1.05rem; height: 1.05rem; }

.np__pestanas { display: flex; gap: 0.3rem; margin: 0.2rem 1rem 0.5rem; padding: 0.22rem; border-radius: 999px; background: #e6f0e9; flex-shrink: 0; }
.np__pestanas button { flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.4rem; padding: 0.45rem; border: none; border-radius: 999px; background: none; font-family: inherit; font-size: 0.82rem; font-weight: 700; color: var(--eca-ink-soft); cursor: pointer; transition: all 0.22s ease; }
.np__pestanas .np__pestana--activa { background: #fff; color: var(--eca-green-700); box-shadow: 0 2px 10px rgba(2, 20, 10, 0.12); }
.np__contador { min-width: 1.15rem; padding: 0 0.35rem; border-radius: 99px; background: #dc2626; color: #fff; font-size: 0.66rem; line-height: 1.15rem; }
.np__aviso-offline { margin: 0 1rem 0.4rem; padding: 0.35rem 0.7rem; border-radius: 10px; background: #fef3c7; color: #92400e; font-size: 0.72rem; font-weight: 700; text-align: center; }

.np__lista { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 0 0.8rem 1rem; -webkit-overflow-scrolling: touch; }
.np__grupo h3 { margin: 0.7rem 0.3rem 0.35rem; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.09em; color: var(--eca-ink-faint); }

.np-tarjeta {
  position: relative; width: 100%; display: flex; align-items: flex-start; gap: 0.7rem;
  padding: 0.75rem 0.8rem; margin-bottom: 0.5rem; text-align: left; font-family: inherit;
  border: 1px solid var(--eca-surface-border); border-radius: 18px; background: #fff; cursor: pointer;
  box-shadow: 0 2px 10px rgba(2, 20, 10, 0.05);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, border-color 0.2s;
}
.np-tarjeta:hover { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(2, 20, 10, 0.1); }
.np-tarjeta:active { transform: scale(0.985); }
.np-tarjeta--nueva { border-color: color-mix(in srgb, var(--c) 35%, #fff); background: linear-gradient(135deg, color-mix(in srgb, var(--c) 7%, #fff), #fff 60%); }
.np-tarjeta__icono { flex-shrink: 0; width: 2.5rem; height: 2.5rem; border-radius: 14px; background: linear-gradient(135deg, var(--c), color-mix(in srgb, var(--c) 65%, #000)); color: #fff; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 14px color-mix(in srgb, var(--c) 40%, transparent); }
.np-tarjeta__icono svg { width: 1.15rem; height: 1.15rem; }
.np-tarjeta__texto { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.12rem; }
.np-tarjeta__meta { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; font-size: 0.64rem; }
.np-tarjeta__meta b { color: var(--c); text-transform: uppercase; letter-spacing: 0.07em; font-weight: 800; }
.np-tarjeta__meta time { color: var(--eca-ink-faint); font-weight: 600; white-space: nowrap; margin-right: 0.9rem; }
.np-tarjeta strong { font-size: 0.92rem; line-height: 1.25; color: var(--eca-ink); overflow-wrap: anywhere; }
.np-tarjeta:not(.np-tarjeta--nueva) strong { font-weight: 600; }
.np-tarjeta em { font-style: normal; font-size: 0.8rem; font-weight: 600; color: var(--eca-ink-soft); overflow-wrap: anywhere; }
.np-tarjeta__desc { font-size: 0.78rem; line-height: 1.4; color: var(--eca-ink-soft); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.np-tarjeta__chip { align-self: flex-start; display: inline-flex; align-items: center; gap: 0.25rem; margin-top: 0.2rem; padding: 0.15rem 0.55rem; border-radius: 99px; background: #eef3ef; font-size: 0.68rem; font-weight: 700; color: var(--eca-ink-soft); }
.np-tarjeta__chip svg { width: 0.65rem; height: 0.65rem; }
.np-tarjeta__miniatura { flex-shrink: 0; width: 3.6rem; height: 3.6rem; border-radius: 12px; overflow: hidden; background: #e8efe9; }
.np-tarjeta__miniatura img { width: 100%; height: 100%; object-fit: cover; display: block; }
.np-tarjeta__punto { position: absolute; top: 0.75rem; right: 0.8rem; width: 0.55rem; height: 0.55rem; border-radius: 50%; background: var(--c); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c) 22%, transparent); animation: np-pulso 2s ease-in-out infinite; }
@keyframes np-pulso { 50% { box-shadow: 0 0 0 6px color-mix(in srgb, var(--c) 8%, transparent); } }

.np-fila-enter-active { transition: transform 0.4s cubic-bezier(0.34, 1.4, 0.64, 1), opacity 0.3s ease; }
.np-fila-enter-from { opacity: 0; transform: translateY(-14px) scale(0.97); }
.np-fila-move { transition: transform 0.3s ease; }

.np__vacio { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.3rem; padding: 3rem 1rem; color: var(--eca-ink-soft); }
.np__vacio-icono { width: 4rem; height: 4rem; border-radius: 50%; background: #e3f1e8; color: var(--eca-green-600); display: flex; align-items: center; justify-content: center; margin-bottom: 0.4rem; }
.np__vacio-icono svg { width: 1.8rem; height: 1.8rem; }
.np__vacio strong { color: var(--eca-ink); font-size: 1rem; }
.np__vacio p { margin: 0; font-size: 0.82rem; }

/* esqueleto */
.np-esqueleto { display: flex; gap: 0.7rem; padding: 0.8rem; margin: 0.5rem 0; border-radius: 18px; background: #fff; border: 1px solid var(--eca-surface-border); }
.np-esqueleto__circulo { width: 2.5rem; height: 2.5rem; border-radius: 14px; background: #e6eee9; flex-shrink: 0; }
.np-esqueleto__lineas { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; padding-top: 0.2rem; }
.np-esqueleto__lineas i { display: block; height: 0.7rem; border-radius: 6px; background: #e6eee9; }
.np-esqueleto__lineas i:last-child { width: 60%; }
.np-esqueleto__circulo, .np-esqueleto__lineas i { background-image: linear-gradient(100deg, transparent 30%, rgba(255, 255, 255, 0.75) 50%, transparent 70%); background-size: 200% 100%; animation: np-brillo 1.3s linear infinite; background-color: #e6eee9; }
@keyframes np-brillo { from { background-position: 150% 0; } to { background-position: -50% 0; } }

/* invitación push */
.np-push { display: flex; align-items: center; gap: 0.7rem; margin: 0 0.8rem 0.5rem; padding: 0.65rem 0.75rem; border-radius: 16px; background: linear-gradient(135deg, #0f4c26, #15803d); color: #fff; flex-shrink: 0; box-shadow: 0 8px 20px rgba(15, 76, 38, 0.28); }
.np-push__icono { flex-shrink: 0; width: 2.2rem; height: 2.2rem; border-radius: 12px; background: rgba(255, 255, 255, 0.18); display: flex; align-items: center; justify-content: center; }
.np-push__icono svg { width: 1.05rem; height: 1.05rem; }
.np-push__texto { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.1rem; }
.np-push__texto strong { font-size: 0.84rem; line-height: 1.2; }
.np-push__texto small { font-size: 0.72rem; opacity: 0.85; line-height: 1.3; }
.np-push__error { color: #fecaca; opacity: 1 !important; font-weight: 700; }
.np-push button { flex-shrink: 0; padding: 0.5rem 1rem; border: none; border-radius: 99px; background: #fff; color: #0f4c26; font-family: inherit; font-weight: 800; font-size: 0.8rem; cursor: pointer; transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1); }
.np-push button:active { transform: scale(0.92); }
.np-push button:disabled { opacity: 0.7; }

/* detalle */
.np-detalle { flex: 1; min-height: 0; overflow-y: auto; padding: 0.4rem 1.1rem 1.4rem; display: flex; flex-direction: column; gap: 0.7rem; overscroll-behavior: contain; animation: np-entra 0.35s cubic-bezier(0.22, 1, 0.36, 1); }
@keyframes np-entra { from { opacity: 0; transform: translateX(18px); } }
.np-detalle h1 { margin: 0; font-size: 1.4rem; line-height: 1.2; color: var(--eca-ink); letter-spacing: -0.015em; overflow-wrap: anywhere; }
.np-detalle__sub { margin: 0; font-size: 1rem; font-weight: 600; color: var(--eca-ink-soft); overflow-wrap: anywhere; }
.np-detalle__desc { margin: 0; font-size: 0.95rem; line-height: 1.6; color: var(--eca-ink); white-space: pre-wrap; overflow-wrap: anywhere; }
.np-detalle__media { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
.np-detalle__media--uno { grid-template-columns: 1fr; }
.np-detalle__media video, .np-detalle__img { width: 100%; border-radius: 18px; overflow: hidden; background: #0b1f14; display: block; }
.np-detalle__media video { max-height: 55dvh; grid-column: 1 / -1; }
.np-detalle__img { padding: 0; border: none; cursor: zoom-in; aspect-ratio: 4 / 3; }
.np-detalle__media--uno .np-detalle__img { aspect-ratio: auto; }
.np-detalle__img img { width: 100%; height: 100%; object-fit: cover; display: block; }
.np-detalle__media--uno .np-detalle__img img { height: auto; max-height: 55dvh; object-fit: contain; background: #0b1f14; }
.np-detalle__boton { align-self: flex-start; display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1.3rem; border: none; border-radius: 999px; font-family: inherit; font-size: 0.92rem; font-weight: 800; color: #fff; cursor: pointer; background: linear-gradient(135deg, var(--c), color-mix(in srgb, var(--c) 70%, #000)); box-shadow: 0 10px 24px color-mix(in srgb, var(--c) 40%, transparent); transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); }
.np-detalle__boton:active { transform: scale(0.95); }
.np-detalle__boton svg { width: 1.05rem; height: 1.05rem; }

.np-visor { position: fixed; inset: 0; z-index: 80; background: rgba(0, 0, 0, 0.92); display: flex; align-items: center; justify-content: center; padding: 1rem; }
.np-visor img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px; }
.np-visor__cerrar { position: absolute; top: max(14px, env(safe-area-inset-top, 0px) + 10px); right: 14px; width: 2.5rem; height: 2.5rem; border: none; border-radius: 50%; background: rgba(255, 255, 255, 0.18); color: #fff; display: flex; align-items: center; justify-content: center; }
.np-visor__cerrar svg { width: 1.1rem; height: 1.1rem; }

@media (prefers-reduced-motion: reduce) {
  .np-tarjeta__punto, .np-esqueleto__circulo, .np-esqueleto__lineas i, .np-detalle { animation: none; }
}
</style>
